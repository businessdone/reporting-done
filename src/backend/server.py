import secrets
from contextlib import asynccontextmanager

from loguru import logger
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bd_core.database import PGSQLClient
from bd_core.auth import create_session_middleware

from config.env import ENV
from database.models import configure_mappings
from backend.views.log_view import get_projects_with_recent_logs
from backend.controllers.log_controller import log_router
from backend.controllers.auth_controller import auth_router
from backend.controllers.task_controller import task_router
from backend.controllers.user_controller import user_router
from backend.controllers.event_controller import event_router
from backend.controllers.project_controller import project_router
from backend.controllers.dashboard_controller import dashboard_router
from backend.controllers.healthcheck_controller import healthcheck_router
from backend.controllers.availability_controller import availability_router
from backend.controllers.new_calendar_controller import new_calendar_router
from backend.exceptions import (
    BackendException,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
)


scheduler = AsyncIOScheduler()


async def scheduled_get_projects_with_recent_logs() -> None:
    try:
        await get_projects_with_recent_logs()
        logger.info("Emails sent to clients successfully.")
    except Exception as e:
        logger.error(f"Error running scheduled task: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Initialize database client using bd-core's PGSQLClient
    app.state.db = PGSQLClient(
        db_user=ENV.DB_USER,
        db_password=ENV.DB_PASSWORD,
        db_host=ENV.DB_HOST,
        db_port=ENV.DB_PORT,
        db_name=ENV.DB_NAME,
    )
    logger.info(
        f"Database client initialized for {ENV.DB_NAME} at {ENV.DB_HOST}:{ENV.DB_PORT}"
    )

    # Configure ORM mappings for bd-core models with reports-specific relationships
    configure_mappings()
    logger.info("ORM mappings configured.")

    trigger = CronTrigger(hour=23, minute=57)

    scheduler.add_job(
        scheduled_get_projects_with_recent_logs,
        trigger,
        id="daily_project_log_job",
        name="Daily Project Logs Retrieval and Email Sending",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("APScheduler started and job added.")

    yield

    # Cleanup
    scheduler.shutdown()
    await app.state.db.close()
    logger.info("Database client closed.")


app = FastAPI(
    title="Reports Done API",
    version="0.1.0",
    lifespan=lifespan,
)


class LogRequestMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.debug(
            f"Request: {request.method} {request.url} Headers: {dict(request.headers)}"
        )
        response: Response = await call_next(request)
        return response


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if "csrftoken" not in request.session:
            request.session["csrftoken"] = secrets.token_hex(32)
        response = await call_next(request)
        return response


class AuthCheckMiddleware(BaseHTTPMiddleware):
    PUBLIC_PATHS = frozenset([
        "/healthcheck",
        "/health",
        "/auth/login",
        "/auth/check",
        "/docs",
        "/openapi.json",
        "/redoc",
    ])
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        if any(path.startswith(p) for p in self.PUBLIC_PATHS):
            return await call_next(request)
        
        user_id = request.session.get("user_id")
        if not user_id:
            return JSONResponse(
                status_code=401,
                content={"detail": "Not authenticated"},
            )
        
        return await call_next(request)


@app.exception_handler(BackendException)
async def backend_exception_handler(request: Request, exc: BackendException):
    status_code = 500
    
    if isinstance(exc, ValidationError):
        status_code = 400
    elif isinstance(exc, AuthenticationError):
        status_code = 401
    elif isinstance(exc, AuthorizationError):
        status_code = 403
    elif isinstance(exc, NotFoundError):
        status_code = 404
    
    return JSONResponse(
        status_code=status_code,
        content={
            "code": exc.code,
            "message": str(exc),
            "details": exc.details,
        },
    )


app.add_middleware(LogRequestMiddleware)
app.add_middleware(AuthCheckMiddleware)
app.add_middleware(CSRFMiddleware)

# Use bd-core's session middleware factory
middleware_class, kwargs = create_session_middleware(
    secret_key=ENV.SECRET_KEY,
    max_age=60 * 60 * 24 * 365 * 10,  # 10 years
    same_site="lax",
    https_only=ENV.ENV == "prod",
)
app.add_middleware(middleware_class, **kwargs)

origins = [ENV.API_URL]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(healthcheck_router, tags=["Health Check"])
app.include_router(auth_router, tags=["Auth"])
app.include_router(user_router, tags=["User"])
app.include_router(project_router, tags=["Project"])
app.include_router(task_router, tags=["Task"])
app.include_router(log_router, tags=["Log"])
app.include_router(event_router, tags=["Event"])
app.include_router(dashboard_router, tags=["Dashboard"])
app.include_router(availability_router, tags=["Availability"])
app.include_router(new_calendar_router, tags=["Calendar"])
