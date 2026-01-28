from sqlalchemy import Date, Table, Column, String, Boolean, ForeignKey

from database.models.mapper import mapper_registry
from core.models import OfficeAvailability

office_availability_table = Table(
    "office_availability",
    mapper_registry.metadata,
    Column("id", String(26), primary_key=True),
    Column("user_id", String(26), ForeignKey("users.id"), nullable=False),
    Column("day", Date, nullable=False),
    Column("present", Boolean, nullable=True, default=False),
)

mapper_registry.map_imperatively(OfficeAvailability, office_availability_table)
