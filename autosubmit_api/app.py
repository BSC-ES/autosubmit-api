import os
import sys
import time
from fastapi.responses import JSONResponse
from autosubmit_api import routers
from autosubmit_api.bgtasks.scheduler import create_scheduler
from autosubmit_api.database import prepare_db
from autosubmit_api.experiment import common_requests as CommonRequests
from autosubmit_api.logger import get_app_logger, logger
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.config import (
    PROTECTION_LEVEL,
    CAS_LOGIN_URL,
    CAS_VERIFY_URL,
    AS_API_ROOT_PATH,
    get_run_background_tasks_on_start,
    get_disable_background_tasks,
)
from fastapi import FastAPI, HTTPException as FastAPIHTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from autosubmit_api import __version__ as APIVersion
from autosubmit_api.middleware import HttpUrlModifyMiddleware

sys.path.insert(0, os.path.abspath("."))

scheduler = create_scheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Beware this lifespan will run on every worker
    """
    # Startup
    yield
    # Shutdown


def create_app():
    """
    Create the FastAPI app. It will run this only once before the server starts when using multiple workers.
    """
    logger.info("PYTHON VERSION: " + sys.version)
    CommonRequests.enforceLocal(logger)

    # Initial read config
    APIBasicConfig.read()
    logger.debug("API Basic config: " + str(APIBasicConfig().props()))
    logger.debug(
        "Env Config: "
        + str(
            {
                "PROTECTION_LEVEL": PROTECTION_LEVEL,
                "CAS_LOGIN_URL": CAS_LOGIN_URL,
                "CAS_VERIFY_URL": CAS_VERIFY_URL,
                "DISABLE_BACKGROUND_TASKS": get_disable_background_tasks(),
                "RUN_BACKGROUND_TASKS_ON_START": get_run_background_tasks_on_start(),
                "AS_API_ROOT_PATH": AS_API_ROOT_PATH,
            }
        )
    )

    # Prepare DB
    prepare_db()

    # Initial background tasks
    scheduler.start()

    return FastAPI(
        root_path=AS_API_ROOT_PATH,
        lifespan=lifespan,
        redirect_slashes=True,
        title="Autosubmit API",
        version=APIVersion,
        license_info={
            "name": "GNU General Public License",
            "url": "https://www.gnu.org/licenses/gpl-3.0.html",
        },
    )


app = create_app()


# Exception handlers


@app.exception_handler(FastAPIHTTPException)
async def http_exception_handler(request: Request, exc: FastAPIHTTPException):
    return JSONResponse(
        content={"error": True, "error_message": exc.detail},
        status_code=exc.status_code,
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        content={"error": True, "error_message": "An unexpected error occurred."},
        status_code=500,
    )


# Middlewares

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_runtime(request: Request, call_next):
    logger = get_app_logger()
    start_time = time.time()
    try:
        path = request.url.path
        if request.url.query:
            path += "?" + request.url.query
        method = request.method
    except Exception:
        path = ""
        method = ""
    logger.info("\033[94m{} {}|RECEIVED\033[0m".format(method, path))
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.error(
            "\033[91m{} {}|ERROR|Exception msg: {}\033[0m".format(
                method, path, str(exc)
            )
        )
        raise exc
    logger.info(
        "\033[92m{} {}|RTIME|{:.3f}s\033[0m".format(
            method, path, (time.time() - start_time)
        )
    )
    return response


# NOTE: Middleware is executed in the inverse order of the order they are added.
# So, the HttpUrlModifyMiddleware should be added at the end.
app.add_middleware(HttpUrlModifyMiddleware)


# Routers

app.include_router(routers.router)
