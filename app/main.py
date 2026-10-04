"""
Main FastAPI application entrypoint for The Blind Spot.
Configures security headers, rate limiting, gzip compression,
CORS, static asset hosting, error handling, and API routing.
"""

import logging
import time
from collections import defaultdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers import analyze_router, followup_router, health_router, map_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("blindspot.main")

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="An AI thinking companion that surfaces blind spots, assumptions, and internal conflicts.",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url=None,
)

# ------------------------------------------------------------------------------
# 1. Gzip Compression Middleware
# ------------------------------------------------------------------------------
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ------------------------------------------------------------------------------
# 2. CORS Middleware (Restricted to same-origin / localhost in development)
# ------------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else ["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------------------
# 3. In-Memory Per-IP Rate Limiter
# ------------------------------------------------------------------------------
_ip_request_records: dict[str, list[float]] = defaultdict(list)


def reset_rate_limiter() -> None:
    """Resets in-memory IP rate limiter records (used for test isolation)."""
    _ip_request_records.clear()


@app.middleware("http")
async def rate_limit_and_security_headers_middleware(request: Request, call_next):
    """
    Combines per-IP rate limiting and security headers injection.
    """
    client_ip = request.client.host if request.client else "unknown"
    path = request.url.path

    # Apply rate limiting only to /api/analyze and /api/followup endpoints
    if path.startswith(("/api/analyze", "/api/followup")):
        now = time.time()
        window_start = now - 60.0  # 1 minute window

        # Filter out timestamps older than 60s
        records = [t for t in _ip_request_records[client_ip] if t > window_start]
        _ip_request_records[client_ip] = records

        if len(records) >= settings.RATE_LIMIT_PER_MINUTE:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Please wait a moment before trying again.",
                    "code": "RATE_LIMIT_EXCEEDED",
                },
            )
        _ip_request_records[client_ip].append(now)

    response: Response = await call_next(request)

    # Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )

    return response


# ------------------------------------------------------------------------------
# 4. Global Exception Handlers
# ------------------------------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Formats validation errors cleanly without internal leaks."""
    errors = []
    for err in exc.errors():
        field = " -> ".join(str(loc) for loc in err.get("loc", []))
        msg = err.get("msg", "Invalid value")
        errors.append(f"{field}: {msg}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error on input: " + "; ".join(errors),
            "code": "VALIDATION_ERROR",
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handles standard HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": "HTTP_ERROR"},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Shields users from internal stack traces."""
    logger.error(f"Unhandled exception on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An unexpected server error occurred. Please try again later.",
            "code": "INTERNAL_SERVER_ERROR",
        },
    )


# ------------------------------------------------------------------------------
# 5. Include API Routers
# ------------------------------------------------------------------------------
app.include_router(health_router)
app.include_router(analyze_router)
app.include_router(followup_router)
app.include_router(map_router)

# ------------------------------------------------------------------------------
# 6. Static Files & Frontend Mount
# ------------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

# Ensure static directory exists
STATIC_DIR.mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "css").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "js").mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=FileResponse, summary="Serve frontend homepage")
async def serve_index():
    """Serves the single page frontend application."""
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend index file not found")
    return FileResponse(str(index_path))
