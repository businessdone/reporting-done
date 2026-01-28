"""Re-export enums from bd-core for backward compatibility."""

from bd_core.enums import (
    FlagBase,
    Permissions,
    ProjectPermissions,
    Roles,
    UserStatus,
    OrganizationStatus,
    ProjectStatus,
    FileStatus,
    SubscriptionTier,
)

# Reports-specific enums (keep local)
from .task_status import TaskStatus

# Reports-specific subscription limits
from .subscription_limits import OCR_PAGE_LIMITS, get_ocr_page_limit

__all__ = [
    "FlagBase",
    "Permissions",
    "ProjectPermissions",
    "Roles",
    "UserStatus",
    "OrganizationStatus",
    "ProjectStatus",
    "FileStatus",
    "SubscriptionTier",
    "TaskStatus",
    # Reports-specific subscription helpers
    "OCR_PAGE_LIMITS",
    "get_ocr_page_limit",
]
