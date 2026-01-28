from typing import List, Tuple
import datetime

from backend.models import TaskCreateModel, TaskResponseModel
from core.models import Log, Task, User, Project
# Note: Task mapping is configured at import time in task_mapper
from backend.models.models import LogResponseModel
from backend.utils.pagination import calculate_pagination
from backend.models.pagination import Pagination
from sqlalchemy.ext.asyncio import AsyncSession
from businessdone_core.database import Repository


async def create_task(task: TaskCreateModel, session: AsyncSession) -> TaskResponseModel:
    """
    Create a new task in the database.
    """
    project_repo = Repository(session, Project)
    project = await project_repo.get(task.project_id)

    if not project:
        raise ValueError(f"Project with ID {task.project_id} not found")

    user_repo = Repository(session, User)
    user = await user_repo.get(task.user_id)

    if not user:
        raise ValueError(f"User with ID {task.user_id} not found")

    repo = Repository(session, Task)

    new_task = Task(
        project_id=project.id,
        project_name=project.name,
        user_id=user.id,
        user_name=user.full_name,
        title=task.title,
        hours_required=task.hours_required,
        description=task.description,
        created_at=datetime.datetime.now(datetime.timezone.utc),
        logs=[],
        status=task.status,
    )

    await repo.create(new_task)
    await session.commit()
    task_data = new_task.to_dict()
    return TaskResponseModel.model_validate(task_data)


async def get_task(session: AsyncSession, **kwargs) -> TaskResponseModel:
    """
    Retrieve a single task from the database based on provided criteria.
    """
    repo = Repository[Task](session, Task)
    project_repo = Repository(session, Project)

    task = await repo.query(**kwargs, options=[Task.logs])  # type: ignore
    if not task:
        raise ValueError("Task not found")
    task_obj = task[0]
    project = await project_repo.get(task_obj.project_id)
    task_dict = task_obj.to_dict()
    task_dict["project_name"] = project.name if project else ""
    return TaskResponseModel.model_validate(task_dict)


async def update_task(
    task_id: str, task_update: TaskCreateModel, session: AsyncSession
) -> TaskResponseModel:
    """
    Update an existing task's information.
    """
    repo = Repository[Task](session, Task)
    task = await repo.get(task_id)
    if not task:
        raise ValueError("Task not found")

    for attr, value in task_update.model_dump().items():
        setattr(task, attr, value)

    await session.commit()
    task_dict = task.to_dict()
    return TaskResponseModel.model_validate(task_dict)


async def upsert_task(
    task: TaskResponseModel, session: AsyncSession
) -> TaskResponseModel:
    """
    Insert a new task or update an existing task based on unique constraints.
    """
    repo = Repository[Task](session, Task)
    project_repo = Repository(session, Project)
    existing_task = await repo.get(task.id)
    project = await project_repo.query(id=task.project_id)
    if existing_task:
        for attr, value in task.model_dump().items():
            setattr(existing_task, attr, value)
        await session.commit()
        task_dict = existing_task.to_dict()
    else:
        new_task = Task(
            project_id=task.project_id,
            project_name=project[0].name,
            user_id=task.user_id,
            user_name=task.user_name,
            title=task.title,
            hours_required=task.hours_required,
            description=task.description,
            status=task.status,
            created_at=datetime.datetime.now(datetime.timezone.utc),
            logs=[],
        )
        await repo.create(new_task)
        await session.commit()
        task_dict = new_task.to_dict()
    return TaskResponseModel.model_validate(task_dict)


async def get_all_tasks(
    session: AsyncSession, pagination: Pagination, **kwargs
) -> Tuple[List[TaskResponseModel], Pagination]:
    repo = Repository(session, Task)
    total = await repo.count(**kwargs)

    order_by = pagination.order_by

    pagination = calculate_pagination(
        total=total,
        page=pagination.current_page or 1,
        per_page=pagination.limit or 25,
    )
    pagination.order_by = order_by

    if total == 0:
        return [], pagination

    tasks = await repo.query(
        order_by=pagination.order_by,
        limit=pagination.limit,
        offset=pagination.offset,
        options=[Task.logs],  # type: ignore
        **kwargs,
    )

    tasks_list = [
        TaskResponseModel.model_validate(task.to_dict()) for task in tasks
    ]

    return tasks_list, pagination


async def get_project_tasks(
    session: AsyncSession, project_id: str, pagination: Pagination, **kwargs
) -> Tuple[List[TaskResponseModel], Pagination]:
    repo = Repository(session, Task)
    total = await repo.count(project_id=project_id, **kwargs)

    order_by = pagination.order_by

    pagination = calculate_pagination(
        total=total,
        page=pagination.current_page or 1,
        per_page=pagination.limit or 25,
    )

    pagination.order_by = order_by

    if total == 0:
        return [], pagination

    tasks = await repo.query(
        project_id=project_id,
        order_by=pagination.order_by,
        limit=pagination.limit,
        offset=pagination.offset,
        options=[Task.logs],  # type: ignore
        **kwargs,
    )

    tasks_list = [
        TaskResponseModel.model_validate(task.to_dict()) for task in tasks
    ]

    return tasks_list, pagination


async def get_user_tasks(
    session: AsyncSession, user_id: str, pagination: Pagination, **kwargs
) -> Tuple[List[TaskResponseModel], Pagination]:
    repo = Repository(session, Task)
    total = await repo.count(user_id=user_id, **kwargs)

    order_by = pagination.order_by

    pagination = calculate_pagination(
        total=total,
        page=pagination.current_page or 1,
        per_page=pagination.limit or 25,
    )

    pagination.order_by = order_by

    if total == 0:
        return [], pagination

    tasks = await repo.query(
        user_id=user_id,
        order_by=pagination.order_by,
        limit=pagination.limit,
        offset=pagination.offset,
        options=[Task.logs],  # type: ignore
        **kwargs,
    )

    tasks_list = [
        TaskResponseModel.model_validate(task.to_dict()) for task in tasks
    ]

    return tasks_list, pagination


async def get_task_logs(
    session: AsyncSession, task_id: str, pagination: Pagination, **kwargs
) -> Tuple[List[LogResponseModel], Pagination]:
    repo = Repository(session, Log)
    total = await repo.count(task_id=task_id, **kwargs)

    order_by = pagination.order_by

    pagination = calculate_pagination(
        total=total,
        page=pagination.current_page or 1,
        per_page=pagination.limit or 25,
    )

    pagination.order_by = order_by

    if total == 0:
        return [], pagination

    logs = await repo.query(
        task_id=task_id,
        order_by=pagination.order_by,
        limit=pagination.limit,
        offset=pagination.offset,
        **kwargs,
    )

    logs_list = [
        LogResponseModel.model_validate(log.to_dict()) for log in logs
    ]

    return logs_list, pagination
