from typing import Dict, List, Tuple
from datetime import UTC, datetime, timedelta

from ulid import ULID
from loguru import logger

from backend.models import LogCreateModel, LogResponseModel
from core.models import Log, Task, User, Project
# Note: Log mapping is configured at import time in log_mapper
from core.enums.task_status import TaskStatus
from backend.utils.templates import templates
from backend.utils.pagination import calculate_pagination
from backend.models.pagination import Pagination
from backend.utils.send_emails import send_email_to_user
from sqlalchemy.ext.asyncio import AsyncSession
from backend.dependencies.db_session import get_session
from businessdone_core.database import Repository


def create_log(log: LogCreateModel, session: AsyncSession) -> LogResponseModel:
    """
    Create a new log in the database.
    """
    with session as s:
        task_repo = Repository(s, Task)
        task = task_repo.get(id=log.task_id)

        user_repo = Repository(s, User)
        user = user_repo.get(id=log.user_id)

        if not user:
            raise ValueError("User not found")

        if not task:
            raise ValueError("Task not found")

        repo = Repository(s, Log)

        timestamp = int(datetime.now().timestamp())

        new_log = Log(
            id=log.id,
            created_at=datetime.now(UTC),
            task_id=log.task_id,
            task_name=task.title,
            description=log.description,
            user_id=task.user_id,
            user_name=user.full_name,
            project_id=task.project_id,
            project_name=task.project_name,
            hours_spent=log.hours_spent,
            task_status=log.task_status,
        )
        if (
            task._status == TaskStatus.DONE
            and new_log._task_status != TaskStatus.DONE
        ):
            task.returned = True
        task.hours_worked += log.hours_spent
        task.status = log.task_status
        task_repo.update(task)

        repo.create(new_log)
        s.commit()
        html_content = templates.get_template("email/log.html").render(
            {"timestamp": timestamp, "task": task, "log": log}
        )
        send_email_to_user(
            to=user.email,
            title=(
                f"[BusinessDone] Daily Report - "
                f"{datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')}"
            ),
            message=html_content,
        )
        log_data = new_log.to_dict()
    return LogResponseModel.model_validate(log_data)


def get_log(session: AsyncSession, **kwargs) -> LogResponseModel:
    """
    Retrieve a single log from the database based on provided criteria.
    """
    with session as s:
        repo = Repository[Log](s, Log)
        log = repo.query(**kwargs)
        if not log:
            raise ValueError("Log not found")
        log_obj = log[0]
        log_dict = log_obj.to_dict()
    return LogResponseModel.model_validate(log_dict)


def update_log(
    log_id: str, log_update: LogCreateModel, session: AsyncSession
) -> LogResponseModel:
    """
    Update an existing log's information.
    """
    with session as s:
        repo = Repository[Log](s, Log)
        log = repo.get(id=log_id)
        if not log:
            raise ValueError("Log not found")

        for attr, value in log_update.model_dump().items():
            setattr(log, attr, value)

        task_repo = Repository(s, Task)
        task = task_repo.get(id=log.task_id)
        if task:
            task.hours_worked += log_update.hours_spent
            task.status = log_update.task_status
            task_repo.update(task)

        s.commit()
        log_dict = log.to_dict()
    return LogResponseModel.model_validate(log_dict)


def upsert_log(log: LogResponseModel, session: AsyncSession) -> LogResponseModel:
    """
    Insert a new log or update an existing log based on unique constraints.
    """
    with session as s:
        repo = Repository[Log](s, Log)
        existing_log = repo.get(id=log.id)
        if existing_log:
            for attr, value in log.model_dump().items():
                setattr(existing_log, attr, value)
            s.commit()
            log_dict = existing_log.to_dict()
        else:
            new_log = Log(
                id=log.id or str(ULID()),
                created_at=log.created_at or datetime.now(UTC),
                task_id=log.task_id,
                task_name=log.task_name,
                description=log.description,
                user_id=log.user_id,
                user_name=log.user_name,
                project_id=log.project_id,
                project_name=log.project_name,
                hours_spent=log.hours_spent,
                task_status=log.task_status,
            )
            repo.create(new_log)
            s.commit()
            log_dict = new_log.to_dict()
    return LogResponseModel.model_validate(log_dict)


def get_all_logs(
    session: AsyncSession, pagination: Pagination, **kwargs
) -> Tuple[List[LogResponseModel], Pagination]:
    with session as s:
        repo = Repository(s, Log)
        total = repo.count(**kwargs)

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
            order_by=pagination.order_by,
            limit=pagination.limit,
            offset=pagination.offset,
            **kwargs,
        )

        logs_list = [
            LogResponseModel.model_validate(log.to_dict()) for log in logs
        ]

    return logs_list, pagination


async def get_projects_with_recent_logs() -> Dict[Project, List[Log]]:
    """
    Retrieves all projects associated with logs from the last 24 hours,
    mapping each project to its corresponding logs.

    Args:
        session (ISession): An instance of the SQLAlchemy session interface.

    Returns:
        Dict[Project, List[Log]]: A dictionary mapping each Project to its related Logs.
    """
    session = await get_session()
    now = datetime.now(UTC)
    past_24h = now - timedelta(hours=24)

    log_repository = Repository(session, Log)
    project_repository = Repository(session, Project)

    recent_logs = log_repository.query(created_at__gte=past_24h)

    logs_by_project_id: Dict[str, List[Log]] = {}
    for log in recent_logs:
        logs_by_project_id.setdefault(log.project_id, []).append(log)

    project_ids = list(logs_by_project_id.keys())

    if not project_ids:
        logger.warning("No projects associated with recent logs.")
        return {}

    projects = project_repository.query(in_={Project.id: project_ids})

    logger.info(
        f"Found {len(recent_logs)} logs from the last 24 hours for {len(project_ids)} projects."
    )

    projects_map: Dict[str, Project] = {
        project.id: project for project in projects
    }

    # Map each Project to its corresponding Logs
    projects_with_logs: Dict[Project, List[Log]] = {}
    for project_id, logs in logs_by_project_id.items():
        project = projects_map.get(project_id)
        if project:
            projects_with_logs[project] = logs
        else:
            print(f"Warning: Project ID {project_id} not found in projects.")

    timestamp = int(datetime.now().timestamp())

    for project, logs in projects_with_logs.items():
        html = templates.get_template("email/multiple_logs.html").render(
            logs=logs,
        )
        if project.email:
            send_email_to_user(
                to=project.email,
                title=(
                    f"[BusinessDone] Daily Project Report - "
                    f"{datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')}"
                ),
                message=html,
            )

    return projects_with_logs
