import os
import sys
import time
from fastapi.responses import JSONResponse
import requests
from flask_cors import CORS
from flask import Flask
from autosubmit_api import routers
from autosubmit_api.bgtasks.scheduler import create_bind_scheduler
from autosubmit_api.blueprints.v3 import create_v3_blueprint
from autosubmit_api.database import prepare_db
from autosubmit_api.experiment import common_requests as CommonRequests
from autosubmit_api.logger import get_app_logger
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.config import (
    PROTECTION_LEVEL,
    CAS_LOGIN_URL,
    CAS_VERIFY_URL,
    get_run_background_tasks_on_start,
    get_disable_background_tasks,
)
from autosubmit_api.views import handle_HTTP_exception
from werkzeug.exceptions import HTTPException
from fastapi import FastAPI, HTTPException as FastAPIHTTPException, Request
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from autosubmit_api import __version__ as APIVersion


def create_app():
    """
    Autosubmit Flask application factory
    This function initializes the application properly
    """

    sys.path.insert(0, os.path.abspath("."))

    app = Flask(__name__)

    # CORS setup
    CORS(app)

    # Logger binding
    app.logger = get_app_logger()
    app.logger.info("PYTHON VERSION: " + sys.version)

    # Enforce Language Locale
    CommonRequests.enforceLocal(app.logger)

    requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += "HIGH:!DH:!aNULL"
    try:
        requests.packages.urllib3.contrib.pyopenssl.DEFAULT_SSL_CIPHER_LIST += (
            "HIGH:!DH:!aNULL"
        )
    except AttributeError:
        app.logger.warning("No pyopenssl support used / needed / available")

    # Initial read config
    APIBasicConfig.read()
    app.logger.debug("API Basic config: " + str(APIBasicConfig().props()))
    app.logger.debug(
        "Env Config: "
        + str(
            {
                "PROTECTION_LEVEL": PROTECTION_LEVEL,
                "CAS_LOGIN_URL": CAS_LOGIN_URL,
                "CAS_VERIFY_URL": CAS_VERIFY_URL,
                "DISABLE_BACKGROUND_TASKS": get_disable_background_tasks(),
                "RUN_BACKGROUND_TASKS_ON_START": get_run_background_tasks_on_start(),
            }
        )
    )

    # Prepare DB
    prepare_db()

    # Background Scheduler
    create_bind_scheduler(app)

    ################################ ROUTES ################################

    v3_blueprint = create_v3_blueprint()
    app.register_blueprint(
        v3_blueprint, name="root"
    )  # Add v3 to root but will be DEPRECATED

    app.register_error_handler(HTTPException, handle_HTTP_exception)

    return app


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown


app = FastAPI(
    lifespan=lifespan,
    redirect_slashes=True,
    title="Autosubmit API",
    version=APIVersion,
    license_info={
        "name": "GNU General Public License",
        "url": "https://www.gnu.org/licenses/gpl-3.0.html",
    },
)


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


app.include_router(routers.router)

flask_app = create_app()
app.mount("/v3", WSGIMiddleware(flask_app), name="flask")
