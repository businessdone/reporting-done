from sqlalchemy import (
    Table,
    Column,
    String,
    DateTime,
    BigInteger,
    ForeignKey,
    func,
)
from sqlalchemy.orm import relationship

from database.models.mapper import mapper_registry
from database.models.user_model import user_table
from core.models import Organization

organization_table = Table(
    "organizations",
    mapper_registry.metadata,
    Column("id", String(26), primary_key=True),
    Column("name", String(255), unique=True),
    Column("subscription", String(50)),
    Column("storage_limit", BigInteger()),
    Column("status", BigInteger(), default=0),
    Column(
        "owner_id",
        String(26),
        ForeignKey(
            "users.id",
            use_alter=True,
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=False,
    ),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), onupdate=func.now()),
)

mapper_registry.map_imperatively(
    Organization,
    organization_table,
    properties={
        "users": relationship(
            "User",
            back_populates="organization",
            cascade="all, delete-orphan",
            lazy="selectin",
            foreign_keys=[user_table.c.organization_id],
        ),
        "projects": relationship(
            "Project",
            back_populates="organization",
            cascade="all, delete-orphan",
            lazy="selectin",
        ),
    },
)
