import os
import sys
import requests
from flask_cors import CORS
from flask import Flask
from autosubmit_api.bgtasks.scheduler import create_bind_scheduler
from autosubmit_api.blueprints.v3 import create_v3_blueprint
from autosubmit_api.blueprints.v4 import create_v4_blueprint
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
from autosubmit_api.views import handle_HTTP_exception, home
from werkzeug.exceptions import HTTPException
from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware
from contextlib import asynccontextmanager

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

    app.route("/")(home)

    v3_blueprint = create_v3_blueprint()
    app.register_blueprint(
        v3_blueprint, name="root"
    )  # Add v3 to root but will be DEPRECATED
    app.register_blueprint(v3_blueprint, url_prefix="/v3")

    v4_blueprint = create_v4_blueprint()
    app.register_blueprint(v4_blueprint, url_prefix="/v4")

    app.register_error_handler(HTTPException, handle_HTTP_exception)

    return app


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    flask_app = create_app()
    app.mount("/", WSGIMiddleware(flask_app), name="flask")
    yield
    # Shutdown


app = FastAPI(lifespan=lifespan)
