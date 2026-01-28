from typing import Any, List, Tuple

from ulid import ULID
from loguru import logger

from backend.models import ProjectCreateModel, ProjectResponseModel
# Note: Project mapping is configured at startup via configure_mappings()
from core.models import Task, User, Project
from backend.models.models import TaskResponseModel, UserResponseModel
from backend.utils.pagination import calculate_pagination
from core.models.project_user import ProjectUser
from backend.models.pagination import Pagination
from sqlalchemy.ext.asyncio import AsyncSession
from bd_core.database import Repository


async def create_project(
    project: ProjectCreateModel, session: AsyncSession
) -> ProjectResponseModel:
    """
    Create a new project in the database.
    """
    new_project = Project(          name=project.name,
        email=project.email,
        send_email=project.send_email,
        archived=project.archived,
        developers=[],
        tasks=[],
    )
    repository = Repository(session, Project)
    await repository.create(new_project)
    await session.commit()
    project_data = new_project.to_dict()
    return ProjectResponseModel.model_validate(project_data)


async def get_project(session: AsyncSession, **kwargs) -> ProjectResponseModel:
    """
    Retrieve a single project from the database based on provided criteria.
    """
    repository = Repository(session, Project)
    project = await repository.query(
        **kwargs,
        options=[Project.developers, Project.tasks],      )

    if not project:
        raise ValueError("Project not found")

    project_dict = project[0].to_dict()

    return ProjectResponseModel.model_validate(project_dict)


async def update_project(
    project_id: str, project_update: ProjectCreateModel, session: AsyncSession
) -> ProjectResponseModel:
    """
    Update an existing project's information.
    """
    repo = Repository[Project](session, Project)
    projects = await repo.query(
        id=project_id, options=[Project.developers, Project.tasks]      )
    project = projects[0] if projects else None

    if not project:
        raise ValueError(f"Project with id {project_id} does not exist.")

    for attr, value in project_update.model_dump(
        exclude_unset=True
    ).items():
        setattr(project, attr, value)

    await session.commit()
    updated_projects = await repo.query(
        id=project_id, options=[Project.developers, Project.tasks]      )
    updated_project_orm = updated_projects[0] if updated_projects else None
    if not updated_project_orm:
        raise ValueError(
            "Project disappeared after update"
        )
    project_data = updated_project_orm.to_dict()
    return ProjectResponseModel.model_validate(project_data)


async def upsert_project(
    project: ProjectCreateModel, session: AsyncSession
) -> ProjectResponseModel:
    """
    Insert a new project or update an existing project based on unique constraints.
    """
    repository = Repository(session, Project)
    existing_project = await repository.query(name=project.name)

    if existing_project:
        project_obj = existing_project[0]
        for key, value in project.model_dump(exclude_unset=True).items():
            setattr(project_obj, key, value)
        await repository.update(project_obj)
    else:
        project_obj = Project(              name=project.name,
            email=project.email,
            send_email=project.send_email,
            archived=project.archived,
        )
        await repository.create(project_obj)

    await session.commit()
    project_dict = project_obj.to_dict()

    return ProjectResponseModel.model_validate(project_dict)


async def get_all_projects(
    session: AsyncSession, pagination: Pagination, **kwargs
) -> Tuple[List[ProjectResponseModel], Pagination]:
    """
    Retrieve paginated projects from the database.

    This function rebuilds the necessary models, queries the database for all projects,
    applies pagination, populates project fields, validates, and returns the project data
    along with pagination information.

    Args:
        session (ISession): The database session used for querying the projects.
        pagination (Pagination): Pagination parameters.
        **kwargs: Additional filtering keyword arguments.

    Returns:
        Tuple[List[ProjectResponseModel], Pagination]: A tuple containing the list of validated response models
                                                        representing the projects and the pagination info.
    """
    repository = Repository(session, Project)

    # Calculate the total number of projects matching the filters
    total = await repository.count(**kwargs)

    order_by = pagination.order_by

    pagination = calculate_pagination(
        total=total,
        page=pagination.current_page or 1,
        per_page=pagination.limit or 25,
    )

    pagination.order_by = order_by

    if total == 0:
        return [], pagination

    projects = await repository.query(
        order_by=pagination.order_by,
        limit=pagination.limit,
        offset=pagination.offset,
        options=[Project.developers, Project.tasks],          **kwargs,
    )

    if not projects:
        return [], pagination

    project_dicts = [project.to_dict() for project in projects]

    output = [
        ProjectResponseModel.model_validate(proj_dict)
        for proj_dict in project_dicts
    ]

    return output, pagination


async def get_users_projects(
    user_id: str, session: AsyncSession, pagination: Pagination, **kwargs
) -> Tuple[List[ProjectResponseModel], Pagination]:
    """
    Retrieve paginated projects associated with a specific user.

    This function rebuilds the necessary models, counts the total number of projects
    associated with the user, applies pagination, retrieves the projects in bulk,
    populates project fields, validates, and returns the project data along with
    pagination information.

    Args:
        user_id (str): The unique identifier of the user.
        session (ISession): The database session used for querying the projects.
        pagination (Pagination): Pagination parameters.
        **kwargs: Additional filtering keyword arguments.

    Returns:
        Tuple[List[ProjectResponseModel], Pagination]: A tuple containing the list of validated
                                                        response models representing the projects
                                                        and the pagination info.

    Raises:
        Exception: If an error occurs during the retrieval process.
    """
    try:
        assoc_repo = Repository(session, ProjectUser)

        pagination = calculate_pagination(
            total=1,
            page=pagination.current_page or 1,
            per_page=pagination.limit or 25,
        )

        associations = await assoc_repo.query(
            user_id=user_id,
            order_by=pagination.order_by,
            limit=pagination.limit,
            offset=pagination.offset,
        )

        project_ids = [assoc.project_id for assoc in associations]

        if not project_ids:
            pagination = calculate_pagination(total=0, page=1, per_page=25)
            return [], pagination

        project_repo = Repository(session, Project)

        projects = await project_repo.query(
            in_={Project.id: project_ids},              options=[Project.developers, Project.tasks],              order_by=pagination.order_by,
            **kwargs,
        )

        pagination = calculate_pagination(
            total=len(projects), page=1, per_page=25
        )

        if not projects:
            return [], pagination

        project_dicts = [project.to_dict() for project in projects]

        output = [
            ProjectResponseModel.model_validate(proj_dict)
            for proj_dict in project_dicts
        ]

        return output, pagination

    except Exception as e:
        logger.exception(
            f"Error retrieving projects for user {user_id}: {str(e)}"
        )
        return [], pagination


async def assign_project_to_user(
    project_id: str, user_id: str, session: AsyncSession
) -> ProjectResponseModel:
    project = await Repository(session, Project).get(project_id)
    user = await Repository(session, User).get(user_id)
    project_user = Repository(session, ProjectUser)

    if not project:
        raise ValueError(f"Project with id {project_id} does not exist.")
    if not user:
        raise ValueError(f"User with id {user_id} does not exist.")

    await project_user.create(
        ProjectUser(id=str(ULID()), project_id=project_id, user_id=user_id)
    )
    await session.commit()

    project_dict = project.to_dict()

    return ProjectResponseModel.model_validate(project_dict)


async def remove_user_from_project(
    project_id: str, user_id: str, session: AsyncSession
) -> ProjectResponseModel:
    project = await Repository(session, Project).get(project_id)
    user = await Repository(session, User).get(user_id)
    project_user_repo = Repository(session, ProjectUser)

    if not project:
        raise ValueError(f"Project with id {project_id} does not exist.")
    if not user:
        raise ValueError(f"User with id {user_id} does not exist.")

    project_users = await project_user_repo.query(
        project_id=project_id, user_id=user_id
    )

    if not project_users:
        raise ValueError(
            f"User {user_id} is not assigned to project {project_id}."
        )

    project_user = project_users[0]
    await project_user_repo.delete(project_user)
    await session.commit()

    project_dict = project.to_dict()

    return ProjectResponseModel.model_validate(project_dict)


async def get_user_by_project(
    session: AsyncSession, project_id: str, pagination: Pagination, **kwargs
) -> Tuple[List[UserResponseModel], Pagination]:
    """
    Retrieve paginated users associated with a project.

    This function rebuilds the necessary models, queries the database for users associated with a
    project, populates developer fields within the user's associated projects, validates,
    and returns the user data along with pagination info.

    Args:
        session (ISession): The database session used for querying the users.
        project_id (str): The unique identifier of the project to filter users.
        pagination (Pagination): Pagination parameters.
        **kwargs: Additional filtering keyword arguments.

    Returns:
        Tuple[List[UserResponseModel], Pagination]: A tuple containing the list of validated response models
                                                    representing the users and the pagination info.

    Raises:
        IndexError: If no users are associated with the specified project.
    """
    assoc_repo = Repository(session, ProjectUser)
    total = await assoc_repo.count(project_id=project_id, **kwargs)

    if total == 0:
        return [], calculate_pagination(
            total=0, page=1, per_page=pagination.limit or 10
        )

    order_by = pagination.order_by

    pagination = calculate_pagination(
        total=total,
        page=pagination.current_page or 1,
        per_page=pagination.limit or 25,
    )

    pagination.order_by = order_by

    result = await assoc_repo.query(
        project_id=project_id,
        order_by=pagination.order_by,
        limit=pagination.limit,
        offset=pagination.offset,
        **kwargs,
    )

    user_ids = [row.user_id for row in result]
    user_repo = Repository(session, User)

    users = await user_repo.query(
        in_={User.id: user_ids},          options=[User.tasks, User.projects],      )

    if not users:
        return [], pagination

    user_dicts = [user.to_dict() for user in users]

    output = [
        UserResponseModel.model_validate(user_dict) for user_dict in user_dicts
    ]

    return output, pagination


async def get_project_tasks(
    session: AsyncSession, project_id: str, pagination: Pagination, **kwargs
) -> Tuple[List[TaskResponseModel], Pagination]:
    """
    Retrieve paginated tasks associated with a project.

    This function rebuilds the necessary models, queries the database for tasks associated with a
    project, populates user fields within the task's associated project, validates,
    and returns the task data along with pagination info.

    Args:
        session (ISession): The database session used for querying the tasks.
        project_id (str): The unique identifier of the project to filter tasks.
        pagination (Pagination): Pagination parameters.
        **kwargs: Additional filtering keyword arguments.

    Returns:
        Tuple[List[TaskResponseModel], Pagination]: A tuple containing the list of validated response models
                                                    representing the tasks and the pagination info.

    Raises:
        IndexError: If no tasks are associated with the specified project.
    """
    task_repo = Repository(session, Task)
    total = await task_repo.count(project_id=project_id, **kwargs)

    if total == 0:
        return [], calculate_pagination(
            total=0, page=1, per_page=pagination.limit or 10
        )

    order_by = pagination.order_by

    pagination = calculate_pagination(
        total=total,
        page=pagination.current_page or 1,
        per_page=pagination.limit or 25,
    )

    pagination.order_by = order_by

    tasks = await task_repo.query(
        project_id=project_id,
        order_by=pagination.order_by,
        limit=pagination.limit,
        offset=pagination.offset,
        **kwargs,
    )

    if not tasks:
        return [], pagination

    task_dicts = [task.to_dict() for task in tasks]

    output = [
        TaskResponseModel.model_validate(task_dict) for task_dict in task_dicts
    ]

    return output, pagination
