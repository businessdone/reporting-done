from sqlalchemy import (
    DateTime,
    Float,
    Table,
    Column,
    String,
    Boolean,
    ForeignKey,
)
from sqlalchemy.orm import relationship, column_property
from sqlalchemy.sql import func, select

from core.models import Log, Task
from database.models.mapper import mapper_registry

task_table = Table(
    "tasks",
    mapper_registry.metadata,
    Column("id", String(26), primary_key=True),
    Column("project_id", String(26), ForeignKey("projects.id"), nullable=False),
    Column("project_name", String(100), nullable=False),
    Column("user_id", String(26), ForeignKey("users.id"), nullable=False),
    Column("user_name", String(100), nullable=False),
    Column("title", String(100), nullable=False),
    Column("hours_required", Float, nullable=False),
    Column("description", String(255), nullable=True),
    Column("status", String(50), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("hours_worked", Float, nullable=False, default=0.0),
    Column("returned", Boolean, nullable=True, default=False),
)

mapper_registry.map_imperatively(
    Task,
    task_table,
    properties={
        "project": relationship(
            "Project",
            back_populates="tasks",
            lazy="noload",
        ),
        "user": relationship(
            "User",
            back_populates="tasks",
            lazy="noload",
        ),
        "logs": relationship(
            "Log",
            back_populates="task",
            cascade="all, delete-orphan",
            lazy="noload",
        ),
        "updated_at": column_property(
            select(func.max(Log.created_at))  # type: ignore
            .where(Log.task_id == task_table.c.id)  # type: ignore
            .correlate_except(Log)
            .scalar_subquery()
        ),
    },
)
