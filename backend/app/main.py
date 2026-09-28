"""FastAPI Application Entrypoint and Lifecycle Factory."""

import re
import uuid
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.v1.router import api_router
from app.config import get_settings
from app.core.exceptions import SIFSentinelException
from app.core.logging import get_logger, setup_logging

settings = get_settings()
logger = get_logger(__name__)


def _get_request_id(request: Request) -> str:
    """Retrieve or generate request traceability identifier."""
    return getattr(getattr(request, "state", None), "request_id", str(uuid.uuid4()))


def _domain_error_code(exc: SIFSentinelException) -> str:
    """Convert domain exception class name to standardized error code."""
    name = exc.__class__.__name__
    if name.endswith("Exception"):
        name = name[:-9]
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).upper()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown routines."""
    setup_logging(log_level=settings.LOG_LEVEL, log_format=settings.LOG_FORMAT)
    logger.info(
        f"Starting {settings.APP_NAME} v{__version__} in [{settings.APP_ENV}] mode"
    )
    yield
    logger.info(f"Shutting down {settings.APP_NAME}")
    try:
        from app.db.session import engine
        await engine.dispose()
        logger.info("Database engine connections successfully closed")
    except Exception as exc:
        logger.warning(f"Error closing database engine on shutdown: {exc}")


def create_app() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=__version__,
        description=(
            "AI/NLP Engine to Detect Serious Injury & Fatality (SIF) Precursors in "
            "Oil India Limited Unsafe-Act/Unsafe-Condition and Near-Miss Reports."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Request Traceability & Access Logging Middleware
    @app.middleware("http")
    async def request_traceability_middleware(request: Request, call_next) -> Response:
        """Deterministic request-level traceability and access logging middleware."""
        start_time = time.perf_counter()
        incoming_id = request.headers.get("X-Request-ID")
        if incoming_id and incoming_id.strip():
            request_id = incoming_id.strip()
        else:
            request_id = str(uuid.uuid4())

        request.state.request_id = request_id
        try:
            response: Response = await call_next(request)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                f"Request failed: {request.method} {request.url.path} ({duration_ms}ms): {exc}",
                exc_info=True,
                extra={
                    "component": "api",
                    "request_id": request_id,
                    "method": request.method,
                    "route": request.url.path,
                    "status": 500,
                    "duration_ms": duration_ms,
                    "exception_category": exc.__class__.__name__,
                },
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                headers={
                    "X-Request-ID": request_id,
                    "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "DENY",
                    "Referrer-Policy": "strict-origin-when-cross-origin",
                },
                content={
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An internal server error occurred.",
                        "details": None,
                        "request_id": request_id,
                    },
                    "detail": "An internal server error occurred.",
                },
            )

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        logger.info(
            f"{request.method} {request.url.path} {response.status_code} ({duration_ms}ms)",
            extra={
                "component": "api",
                "request_id": request_id,
                "method": request.method,
                "route": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response

    # CORS Middleware configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global Exception Handlers
    @app.exception_handler(SIFSentinelException)
    async def handle_domain_exception(request: Request, exc: SIFSentinelException) -> JSONResponse:
        req_id = _get_request_id(request)
        code = _domain_error_code(exc)
        status_code = getattr(exc, "status_code", status.HTTP_400_BAD_REQUEST)
        logger.warning(
            f"Domain exception [{code}] on {request.url.path} (request_id={req_id}): {exc.message}",
            extra={
                "component": "api",
                "request_id": req_id,
                "method": request.method,
                "route": request.url.path,
                "status": status_code,
                "exception_category": exc.__class__.__name__,
            },
        )
        return JSONResponse(
            status_code=status_code,
            headers={"X-Request-ID": req_id},
            content={
                "error": {
                    "code": code,
                    "message": exc.message,
                    "details": exc.details,
                    "request_id": req_id,
                },
                "message": exc.message,
                "details": exc.details,
                "detail": exc.message,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        req_id = _get_request_id(request)
        logger.warning(
            f"Validation error on {request.url.path} (request_id={req_id}): {exc.errors()}",
            extra={
                "component": "api",
                "request_id": req_id,
                "method": request.method,
                "route": request.url.path,
                "status": status.HTTP_422_UNPROCESSABLE_ENTITY,
                "exception_category": "RequestValidationError",
            },
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            headers={"X-Request-ID": req_id},
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request payload failed schema validation",
                    "details": exc.errors(),
                    "request_id": req_id,
                },
                "message": "Request payload failed schema validation",
                "details": exc.errors(),
                "detail": exc.errors(),
            },
        )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
        req_id = _get_request_id(request)
        detail = exc.detail

        if exc.status_code == status.HTTP_404_NOT_FOUND:
            code = "RESOURCE_NOT_FOUND"
        elif exc.status_code == status.HTTP_400_BAD_REQUEST:
            if isinstance(detail, str) and ("date range" in detail.lower() or "from_date" in detail.lower()):
                code = "INVALID_DATE_RANGE"
            else:
                code = "BAD_REQUEST"
        elif exc.status_code == status.HTTP_409_CONFLICT:
            code = "CONFLICT"
        elif exc.status_code == status.HTTP_501_NOT_IMPLEMENTED:
            code = "NOT_IMPLEMENTED"
        else:
            code = f"HTTP_{exc.status_code}"

        message = detail if isinstance(detail, str) else "HTTP request error"
        details = detail if isinstance(detail, dict) else None

        logger.info(
            f"HTTPException [{code}] on {request.url.path} status={exc.status_code} (request_id={req_id}): {message}",
            extra={
                "component": "api",
                "request_id": req_id,
                "method": request.method,
                "route": request.url.path,
                "status": exc.status_code,
                "exception_category": "HTTPException",
            },
        )

        return JSONResponse(
            status_code=exc.status_code,
            headers={"X-Request-ID": req_id},
            content={
                "error": {
                    "code": code,
                    "message": message,
                    "details": details,
                    "request_id": req_id,
                },
                "detail": detail,
                "message": message,
            },
        )

    @app.exception_handler(Exception)
    async def handle_unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
        req_id = _get_request_id(request)
        logger.error(
            f"Unhandled internal server error on {request.url.path} (request_id={req_id}): {exc}",
            exc_info=True,
            extra={
                "component": "api",
                "request_id": req_id,
                "method": request.method,
                "route": request.url.path,
                "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "exception_category": exc.__class__.__name__,
            },
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            headers={"X-Request-ID": req_id},
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An internal server error occurred.",
                    "details": None,
                    "request_id": req_id,
                },
                "detail": "An internal server error occurred.",
            },
        )

    # Mount API v1 Router
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()
