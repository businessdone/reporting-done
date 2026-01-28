from typing import List, Tuple, Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from backend.models import (
    UserCreateModel,
    UserResponseModel,
    ProjectResponseModel,
    UserProfileUpdateModel,
)
from core.models.log import Log
from database.models import user_table  # noqa F401 - Import to register User mapping
from core.models.task import Task
from core.models.user import User
from core.models.project import Project
from backend.models.models import LogResponseModel, TaskResponseModel
from backend.utils.pagination import calculate_pagination
from core.models.project_user import ProjectUser
from backend.models.pagination import Pagination
from database.interfaces.session import ISession
from database.repositories.repository import Repository


def create_user(user: UserCreateModel, session: ISession) -> UserResponseModel:
    """
    Create a new user in the database.

    This function initializes the user response model, creates a new `User` instance with the provided
    details, and persists it to the database using the provided session. After creation, it validates
    and returns the newly created user as a `UserResponseModel`.

    Args:
        user (UserCreateModel): An instance containing the user's creation data.
        session (ISession): The database session used for interacting with the database.

    Returns:
        UserResponseModel: A validated response model representing the newly created user.
    """
    from core.enums import Roles, SubscriptionTier, get_ocr_page_limit

    ph = PasswordHasher()
    hashed_password = ph.hash(user.password)

    # Split full_name into name and last_name
    name_parts = user.full_name.split(" ", 1)
    name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    new_user = User(
        email=user.email,
        password=hashed_password,
        name=name,
        last_name=last_name,
        subscription=SubscriptionTier.FREE.value,
        role_type=Roles.EDITOR.value,
        limit=get_ocr_page_limit(SubscriptionTier.FREE),
        permissions=user.permissions,
        projects=[],
        tasks=[],
    )
    with session as s:
        repository = Repository(s, User)
        created_user = repository.create(new_user)
        user_data = created_user.to_dict()
    return UserResponseModel.model_validate(user_data)


def authenticate_user(
    email: str, password: str, session: ISession
) -> Optional[User]:
    with session as s:
        repository = Repository(s, User)
        users = repository.query(email=email)
        if not users:
            return None
        user = users[0]
        ph = PasswordHasher()
        try:
            ph.verify(user.password, password)
            return user
        except VerifyMismatchError:
            return None


def get_user(session: ISession, **kwargs) -> UserResponseModel:
    """
    Retrieve a single user from the database based on provided criteria.

    This function rebuilds the project and user response models, queries the database for a user
    matching the provided keyword arguments, and populates developer fields within the user's
    associated projects. It then validates and returns the user data as a `UserResponseModel`.

    Args:
        session (ISession): The database session used for querying the user.
        **kwargs: Arbitrary keyword arguments representing the query parameters to filter the user.

    Returns:
        UserResponseModel: A validated response model representing the retrieved user.

    Raises:
        IndexError: If no user matches the provided criteria.
    """
    with session as s:
        repository = Repository(s, User)
        user = repository.query(**kwargs)[0]
        user_dict = user.to_dict()

    return UserResponseModel.model_validate(user_dict)


def update_user(
    user_id: str, user_update_data: UserProfileUpdateModel, session: ISession
) -> UserResponseModel:
    """
    Update an existing user's profile information (name, last_name, email).

    This function rebuilds the necessary models, retrieves the existing user by `user_id`, and updates
    the user's attributes with the provided `user_update_data` data. It then persists the changes to the
    database, populates developer fields, and returns the updated user as a `UserResponseModel`.

    Args:
        user_id (str): The unique identifier of the user to update.
        user_update_data (UserProfileUpdateModel): An instance containing the updated user data (full_name, email).
        session (ISession): The database session used for interacting with the database.

    Returns:
        UserResponseModel: A validated response model with the updated user data.

    Raises:
        ValueError: If a user with the specified `user_id` does not exist.
    """
    with session as s:
        repository = Repository(s, User)
        existing_user = repository.get(user_id)

        if not existing_user:
            raise ValueError(f"User with id {user_id} does not exist.")

        # Get data from UserProfileUpdateModel, only fields that are set (not None)
        update_data = user_update_data.model_dump(exclude_unset=True)

        # Ensure only allowed fields are updated and no password/permissions here
        allowed_fields_to_update = ["full_name", "email", "permissions"]

        something_updated = False
        for key, value in update_data.items():
            if key in allowed_fields_to_update:
                # Handle full_name -> name/last_name conversion
                if key == "full_name":
                    name_parts = value.split(" ", 1)
                    existing_user.name = name_parts[0]
                    existing_user.last_name = name_parts[1] if len(name_parts) > 1 else ""
                else:
                    setattr(existing_user, key, value)
                something_updated = True
            # else: log a warning or ignore fields not in allowed_fields_to_update

        if something_updated:
            repository.update(existing_user)
        # else: no actual changes were made to allowed fields

    return UserResponseModel.model_validate(existing_user.to_dict())


def upsert_user(user: UserCreateModel, session: ISession) -> UserResponseModel:
    """
    Insert a new user or update an existing user based on unique constraints.

    This function attempts to find an existing user by unique fields (e.g., email). If the user exists,
    it updates the user's attributes with the provided data. If the user does not exist, it creates a
    new user. After upserting, it populates developer fields and returns the user as a
    `UserResponseModel`.

    Args:
        user (UserCreateModel): An instance containing the user data for upserting.
        session (ISession): The database session used for interacting with the database.

    Returns:
        UserResponseModel: A validated response model with the upserted user data.
    """
    from core.enums import Roles, SubscriptionTier, get_ocr_page_limit

    with session as s:
        repository = Repository(s, User)
        existing_user = repository.query(email=user.email)

        if existing_user:
            user_obj = existing_user[0]
            update_data = user.model_dump(exclude_unset=True)
            # Handle full_name -> name/last_name conversion for updates
            if "full_name" in update_data:
                name_parts = update_data.pop("full_name").split(" ", 1)
                update_data["name"] = name_parts[0]
                update_data["last_name"] = name_parts[1] if len(name_parts) > 1 else ""
            for key, value in update_data.items():
                setattr(user_obj, key, value)
            repository.update(user_obj)
        else:
            # Split full_name into name and last_name
            name_parts = user.full_name.split(" ", 1)
            name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ""

            user_obj = User(
                email=user.email,
                password=user.password,
                name=name,
                last_name=last_name,
                subscription=SubscriptionTier.FREE.value,
                role_type=Roles.EDITOR.value,
                limit=get_ocr_page_limit(SubscriptionTier.FREE),
                permissions=user.permissions,
            )
            repository.create(user_obj)

    return UserResponseModel.model_validate(user_obj.to_dict())


def get_all_users(
    session: ISession, pagination: Pagination, **kwargs
) -> Tuple[List[UserResponseModel], Pagination]:
    with session as s:
        repository = Repository(s, User)
        total = repository.count(**kwargs)

        order_by = pagination.order_by

        pagination = calculate_pagination(
            total=total,
            page=pagination.current_page or 1,
            per_page=pagination.limit or 25,
        )

        pagination.order_by = order_by

        if total == 0:
            return [], pagination

        query = repository.query(
            order_by=pagination.order_by,
            limit=pagination.limit,
            offset=pagination.offset,
            options=[User.tasks, User.projects],  # type: ignore
            **kwargs,
        )

        user_models = [
            UserResponseModel.model_validate(user.to_dict()) for user in query
        ]
        return user_models, pagination


def get_user_tasks(
    session: ISession, user_id: str, pagination: Pagination
) -> Tuple[List[TaskResponseModel], Pagination]:
    """
    Retrieve all tasks associated with a user.

    This function rebuilds the necessary models, queries the database for all tasks associated with a
    user, and populates user fields within the task's associated project. It then validates and
    returns the task data as a list of `TaskResponseModel`.

    Args:
        session (ISession): The database session used for querying the tasks.
        user_id (str): The unique identifier of the user to filter tasks.

    Returns:
        List[TaskResponseModel]: A list of validated response models representing the tasks.
    """
    with session as s:
        repository = Repository(s, Task)
        tasks = repository.query(user_id=user_id)

        total = len(tasks)

        order_by = pagination.order_by

        pagination = calculate_pagination(
            total=total,
            page=pagination.current_page or 1,
            per_page=pagination.limit or 25,
        )

        pagination.order_by = order_by

        if not tasks or total == 0:
            return [], pagination

        task_dicts = [task.to_dict() for task in tasks]

    output = [
        TaskResponseModel.model_validate(task_dict) for task_dict in task_dicts
    ]

    return output, pagination


def get_project_by_user(
    session: ISession, user_id: str, pagination: Pagination, **kwargs
) -> Tuple[List[ProjectResponseModel], Pagination]:
    """
    Retrieve paginated projects associated with a user.

    Args:
        session (ISession): The database session used for querying the projects.
        user_id (str): The unique identifier of the user to filter projects.
        pagination (Pagination): Pagination parameters.

    Returns:
        Tuple[List[ProjectResponseModel], Pagination]: Tuple of project list and pagination info.

    Raises:
        IndexError: If no projects are associated with the specified user.
    """
    with session as s:
        repository = Repository(s, Project)
        project_user_repository = Repository(s, ProjectUser)

        total = project_user_repository.count(user_id=user_id, **kwargs)
        project_ids = [
            association.project_id
            for association in project_user_repository.query(
                user_id=user_id, **kwargs
            )
        ]

        order_by = pagination.order_by

        pagination = calculate_pagination(
            total=total,
            page=pagination.current_page or 1,
            per_page=pagination.limit or 25,
        )

        pagination.order_by = order_by

        if total == 0:
            return [], pagination

        projects = repository.query(
            order_by=pagination.order_by,
            limit=pagination.limit,
            offset=pagination.offset,
            in_={Project.id: project_ids},  # type: ignore
            **kwargs,
        )

        if not projects:
            return [], pagination

        project_dicts = [project.to_dict() for project in projects]

    output = [
        ProjectResponseModel.model_validate(project)
        for project in project_dicts
    ]

    return output, pagination


def get_user_logs(
    session: ISession, user_id: str, pagination: Pagination, **kwargs
) -> Tuple[List[LogResponseModel], Pagination]:
    with session as s:
        repo = Repository(s, Log)
        total = repo.count(user_id=user_id, **kwargs)

        order_by = pagination.order_by

        pagination = calculate_pagination(
            total=total,
            page=pagination.current_page or 1,
            per_page=pagination.limit or 25,
        )

        pagination.order_by = order_by

        if total == 0:
            return [], pagination

        logs = repo.query(
            user_id=user_id,
            order_by=pagination.order_by,
            limit=pagination.limit,
            offset=pagination.offset,
            **kwargs,
        )

        logs_list = [
            LogResponseModel.model_validate(log.to_dict()) for log in logs
        ]

    return logs_list, pagination
