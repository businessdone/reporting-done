from random import choice, randint
from datetime import date, datetime, timedelta

from ulid import ULID
from argon2 import PasswordHasher

from core.models.log import Log
from core.models.task import Task
from core.models.user import User
from core.models.project import Project
from core.enums import Permissions
from core.enums.task_status import TaskStatus
from database.adapters.postgresql import PostgreSQL
from core.models.project_user import ProjectUser
import database.models.log_mapper  # noqa: F401
import database.models.task_mapper  # noqa: F401
import database.models.user_mapper  # noqa: F401
import database.models.event_mapper  # noqa: F401
import database.models.project_mapper  # noqa: F401
from core.models.office_availability import OfficeAvailability
from database.repositories.repository import Repository
import database.models.availability_mapper  # noqa: F401
from database.sessions.sqlalchemy_session import SQLAlchemySession

ph = PasswordHasher()
hashed_password = ph.hash("password")

users = [
    User(
        id=str(ULID()),
        full_name=f"John Doe{i}",
        email=f"john.doe{i}@mail.com",
        password=hashed_password,
        permissions=Permissions.DEVELOPER.value,
        projects=[],
        tasks=[],
    )
    for i in range(100)
]
users.append(
    User(
        id=str(ULID()),
        full_name="Jane Doe",
        email="jane.doe@mail.com",
        password=hashed_password,
        permissions=Permissions.ADMIN.value,
        projects=[],
        tasks=[],
    )
)

projects = [
    Project(
        id=str(ULID()),
        name=f"Project {i}",
        email=f"project{i}@mail.com",
        send_email=(i % 2 == 0),
        archived=(i % 2 != 0),
        developers=[],
        tasks=[],
    )
    for i in range(10)
]

seen_pairs = set()
project_users = []
while len(project_users) < 100:
    project_id = choice(projects).id
    user_id = choice(users).id
    pair = (project_id, user_id)

    if pair not in seen_pairs:
        seen_pairs.add(pair)
        project_users.append(
            ProjectUser(
                id=str(ULID()),
                project_id=project_id,
                user_id=user_id,
            )
        )

tasks = []
for i in range(100):
    project = choice(projects)
    user = choice(users)
    hours_required = float(i + 1)
    hours_worked = float(randint(0, i + 1))
    task = Task(
        id=str(ULID()),
        project_id=project.id,
        project_name=project.name,
        user_id=user.id,
        user_name=user.full_name,
        title=f"Task {i}",
        hours_required=hours_required,
        hours_worked=hours_worked,
        returned=(i % 5 == 0),
        description=f"Task {i} description",
        status=choice([status.value for status in TaskStatus]),
        timestamp=int(datetime.now().timestamp()) + (i * 1000),
        logs=[],
    )
    tasks.append(task)

logs = []
for i in range(100):
    task = choice(tasks)
    user = choice(users)
    log = Log(
        id=str(ULID()),
        task_id=task.id,
        user_id=user.id,
        user_name=user.full_name,
        project_id=task.project_id,
        project_name=task.project_name,
        description=f"Task {i} log description",
        timestamp=int(datetime.now().timestamp()),
        hours_spent_today=float(i + 1),
        task_status=task.status,
        task_name=task.title,
    )
    logs.append(log)

availabilities = []
today = date.today()
for user in users:
    for day_offset in range(30):
        day = today - timedelta(days=day_offset)
        availability = OfficeAvailability(
            user_id=user.id,
            day=day,
            present=choice([True, False]),
        )
        availabilities.append(availability)

with SQLAlchemySession(PostgreSQL.session()) as s:
    user_repo = Repository(s, User)
    project_repo = Repository(s, Project)
    task_repo = Repository(s, Task)
    log_repo = Repository(s, Log)
    project_user_table = Repository(s, ProjectUser)
    availability_repo = Repository(s, OfficeAvailability)

    for user in users:
        user_repo.create(user)
    for project in projects:
        project_repo.create(project)
    for task in tasks:
        task_repo.create(task)
    for log in logs:
        log_repo.create(log)
    for project_user in project_users:
        project_user_table.create(project_user)
    for availability in availabilities:
        availability_repo.create(availability)
