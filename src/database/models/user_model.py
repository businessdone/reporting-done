from sqlalchemy import (
    Table,
    Column,
    String,
    Boolean,
    Integer,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.orm import relationship

from core.enums import Roles
from core.models.user import User
from database.models.mapper import mapper_registry

user_table = Table(
    "users",
    mapper_registry.metadata,
    Column("id", String(26), primary_key=True),
    Column("email", String(255), nullable=False, unique=True),
    Column("password", String(255), nullable=False),
    Column("name", String(255), nullable=False),
    Column("last_name", String(255), nullable=False),
    Column("phone", String(20)),
    Column(
        "organization_id",
        String(26),
        ForeignKey(
            "organizations.id",
            use_alter=True,
            deferrable=True,
            initially="DEFERRED",
        ),
    ),
    Column("role_type", Integer(), nullable=False, default=Roles.EDITOR.value),
    Column("permissions", Integer(), nullable=False),
    Column("month_usage", Integer(), default=0),
    Column("is_verified", Boolean(), default=False),
    Column("status", Integer(), default=0),
    Column("subscription", String(50), nullable=False),
    Column("limit", Integer(), nullable=False),
    Column("last_login", DateTime(timezone=True)),
    Column("failed_login_attempts", Integer(), default=0),
    Column("monthly_at", DateTime(timezone=True)),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), onupdate=func.now()),
    Column("stripe_customer_id", String(255), nullable=True),
    Column("stripe_subscription_id", String(255), nullable=True),
    Column("subscription_status", String(50), nullable=True),
    Column("trial_end_date", DateTime(timezone=True), nullable=True),
    Column("default_payment_method_id", String(255), nullable=True),
    Column("subscription_start_date", DateTime(timezone=True), nullable=True),
    Column("subscription_cancel_date", DateTime(timezone=True), nullable=True),
    Column("stripe_price_id", String(255), nullable=True),
    Column("stripe_subscription_item_id", String(255), nullable=True),
    Column("password_reset_required", Boolean(), default=False, nullable=False),
)

mapper_registry.map_imperatively(
    User,
    user_table,
    properties={
        "projects": relationship(
            "Project", back_populates="user", lazy="selectin"
        ),
        "project_memberships": relationship(
            "Project",
            secondary="project_members",
            back_populates="members",
            lazy="selectin",
        ),
        "organization": relationship(
            "Organization",
            back_populates="users",
            lazy="selectin",
            foreign_keys=[user_table.c.organization_id],
        ),
        "tasks": relationship(
            "Task",
            back_populates="user",
            cascade="all, delete-orphan",
            lazy="selectin",
        ),
        "task_logs": relationship(
            "Log",
            back_populates="user",
            cascade="all, delete-orphan",
            lazy="selectin",
        ),
    },
)
