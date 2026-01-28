from backend.dependencies.db_session import get_db_session, get_session
from backend.dependencies.auth import (
    get_current_user,
    get_current_user_optional,
    require_admin,
    is_admin,
    validate_csrf,
)
from backend.dependencies.services import (
    get_auth_service,
    get_user_service,
    get_project_service,
    get_task_service,
    get_log_service,
    get_availability_service,
    get_pagination_service,
)

__all__ = [
    "get_db_session",
    "get_session",  # Alias for backward compatibility
    "get_current_user",
    "get_current_user_optional",
    "require_admin",
    "is_admin",
    "validate_csrf",
    "get_auth_service",
    "get_user_service",
    "get_project_service",
    "get_task_service",
    "get_log_service",
    "get_availability_service",
    "get_pagination_service",
]
