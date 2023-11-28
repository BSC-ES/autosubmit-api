from http import HTTPStatus
import os
import sys
import requests
from flask_cors import CORS
from flask import Flask
from autosubmit_api.bgtasks.scheduler import create_bind_scheduler
from autosubmit_api.blueprints.v3 import create_v3_blueprint
from autosubmit_api.blueprints.v4 import create_v4_blueprint
from autosubmit_api.database.extended_db import ExtendedDB
from autosubmit_api.experiment import common_requests as CommonRequests
from autosubmit_api.logger import get_app_logger
from autosubmit_api.config.basicConfig import APIBasicConfig
import sys
from autosubmit_api.config import (
    PROTECTION_LEVEL,
    RUN_BACKGROUND_TASKS_ON_START,
    CAS_LOGIN_URL,
    CAS_VERIFY_URL,
)
from autosubmit_api.views import home, not_implemented_handler


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
                "RUN_BACKGROUND_TASKS_ON_START": RUN_BACKGROUND_TASKS_ON_START,
            }
        )
    )

    # Prepare DB
    ext_db = ExtendedDB(
        APIBasicConfig.DB_DIR, APIBasicConfig.DB_FILE, APIBasicConfig.AS_TIMES_DB
    )
    ext_db.prepare_db()

    # Background Scheduler
    create_bind_scheduler(app)

    ################################ ROUTES ################################

    app.route("/")(home)

    v3_blueprint = create_v3_blueprint()
    app.register_blueprint(v3_blueprint, url_prefix="/v3")

    v4_blueprint = create_v4_blueprint()
    app.register_blueprint(v4_blueprint, url_prefix="/v4")

    app.register_error_handler(HTTPStatus.NOT_IMPLEMENTED, not_implemented_handler)

    return app
