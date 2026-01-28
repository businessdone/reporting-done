from sqlalchemy import Date, DateTime, Table, Column, String, Time, ForeignKey
from sqlalchemy.orm import relationship

from core.models import Event
from database.models.mapper import mapper_registry

event_table = Table(
    "events",
    mapper_registry.metadata,
    Column("id", String(26), primary_key=True),
    Column("user_id", String(26), ForeignKey("users.id"), nullable=False),
    Column("title", String(255), nullable=False),
    Column("description", String(1000), nullable=True),
    Column("event_type", String(50), nullable=False),
    Column("event_date", Date, nullable=False),
    Column("start_time", Time, nullable=True),
    Column("end_time", Time, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

mapper_registry.map_imperatively(
    Event,
    event_table,
    properties={
        "user": relationship(
            "User",
            lazy="noload",
        ),
    },
)
