from sqlalchemy import DateTime, Float, Table, Column, String, ForeignKey
from sqlalchemy.orm import relationship

from core.models import Log
from database.models.mapper import mapper_registry

task_log_table = Table(
    "task_logs",
    mapper_registry.metadata,
    Column("id", String(26), primary_key=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("task_id", String(26), ForeignKey("tasks.id"), nullable=False),
    Column("task_name", String(100), nullable=False),
    Column("description", String(255), nullable=True),
    Column("user_id", String(26), ForeignKey("users.id"), nullable=False),
    Column("user_name", String(50), nullable=False),
    Column("project_id", String(26), ForeignKey("projects.id"), nullable=False),
    Column("project_name", String(100), nullable=False),
    Column("hours_spent", Float, nullable=False),
    Column("task_status", String(50), nullable=False),
)

mapper_registry.map_imperatively(
    Log,
    task_log_table,
    properties={
        "task": relationship(
            "Task",
            back_populates="logs",
            lazy="noload",
        ),
        "user": relationship(
            "User",
            back_populates="task_logs",
            lazy="noload",
        ),
    },
)
