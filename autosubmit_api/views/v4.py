from datetime import datetime, timedelta
from http import HTTPStatus
import math
import traceback
from typing import Optional
from flask import redirect, request
from flask.views import MethodView
import jwt
from autosubmit_api.auth import ProtectionLevels, with_auth_token
from autosubmit_api.builders.experiment_builder import ExperimentBuilder
from autosubmit_api.builders.experiment_history_builder import (
    ExperimentHistoryBuilder,
    ExperimentHistoryDirector,
)
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database.common import (
    create_main_db_conn,
    execute_with_limit_offset,
)
from autosubmit_api.database.db_common import update_experiment_description_owner
from autosubmit_api.database.queries import generate_query_listexp_extended
from autosubmit_api.logger import logger, with_log_run_times
from autosubmit_api.views import v3
from cas import CASClient
from autosubmit_api.config import (
    JWT_SECRET,
    JWT_ALGORITHM,
    JWT_EXP_DELTA_SECONDS,
    CAS_SERVER_URL,
)


PAGINATION_LIMIT_DEFAULT = 12


class CASV2Login(MethodView):
    decorators = [with_log_run_times(logger, "CASV2LOGIN")]

    def get(self):
        ticket = request.args.get("ticket")
        service = request.args.get("service", request.base_url)

        is_allowed_service = False
        APIBasicConfig.read()
        for allowed_client in APIBasicConfig.ALLOWED_CLIENTS:
            if (allowed_client == "*") or (allowed_client in service) or (service == request.base_url):
                is_allowed_service = True
            

        if not is_allowed_service:
            return {
                "authenticated": False,
                "user": None,
                "token": None,
                "message": "Your service is not authorized for this operation. The API admin needs to add your URL to the list of allowed clients.",
            }, HTTPStatus.UNAUTHORIZED

        cas_client = CASClient(
            version=2, service_url=service, server_url=CAS_SERVER_URL
        )

        if not ticket:
            # No ticket, the request come from end user, send to CAS login
            cas_login_url = cas_client.get_login_url()
            return redirect(cas_login_url)

        # There is a ticket, the request come from CAS as callback.
        # need call `verify_ticket()` to validate ticket and get user profile.
        user, attributes, pgtiou = cas_client.verify_ticket(ticket)

        if not user:
            return {
                "authenticated": False,
                "user": None,
                "token": None,
                "message": "Can't verify user",
            }, HTTPStatus.UNAUTHORIZED
        else:  # Login successful
            payload = {
                "user_id": user,
                "sub": user,
                "iat": int(datetime.now().timestamp()),
                "exp": (datetime.utcnow() + timedelta(seconds=JWT_EXP_DELTA_SECONDS)),
            }
            jwt_token = jwt.encode(payload, JWT_SECRET, JWT_ALGORITHM)
            return {
                "authenticated": True,
                "user": user,
                "token": jwt_token,
                "message": "Token generated",
            }, HTTPStatus.OK


class AuthJWTVerify(MethodView):
    decorators = [
        with_auth_token(threshold=ProtectionLevels.NONE, response_on_fail=False),
        with_log_run_times(logger, "JWTVRF")
    ]

    def get(self, user_id: Optional[str] = None):
        return {
            "authenticated": True if user_id else False,
            "user": user_id,
        }, HTTPStatus.OK if user_id else HTTPStatus.UNAUTHORIZED


class ExperimentView(MethodView):
    # IMPORTANT: Remember that in MethodView last decorator is executed first
    decorators = [with_auth_token(), with_log_run_times(logger, "SEARCH4")]

    def get(self, user_id: Optional[str] = None):
        """
        Search experiments view targeted to handle args
        """
        # Parse args
        logger.debug("Search args: " + str(request.args))

        query = request.args.get("query")
        only_active = request.args.get("only_active") == "true"
        owner = request.args.get("owner")
        exp_type = request.args.get("exp_type")

        order_by = request.args.get("order_by")
        order_desc = request.args.get("order_desc") == "true"

        try:
            page = max(request.args.get("page", default=1, type=int), 1)
            page_size = request.args.get(
                "page_size", default=PAGINATION_LIMIT_DEFAULT, type=int
            )
            if page_size > 0:
                offset = (page - 1) * page_size
            else:
                page_size = None
                offset = None
        except:
            return {
                "error": True,
                "error_message": "Bad Request: invalid params",
            }, HTTPStatus.BAD_REQUEST

        # Query
        statement = generate_query_listexp_extended(
            query=query,
            only_active=only_active,
            owner=owner,
            exp_type=exp_type,
            order_by=order_by,
            order_desc=order_desc,
        )
        with create_main_db_conn() as conn:
            query_result, total_rows = execute_with_limit_offset(
                statement=statement,
                conn=conn,
                limit=page_size,
                offset=offset,
            )

        # Process experiments
        experiments = []
        for raw_exp in query_result:
            exp_builder = ExperimentBuilder()
            exp_builder.produce_base_from_dict(raw_exp._mapping)

            # Get additional data from config files
            try:
                exp_builder.produce_config_data()
            except Exception as exc:
                logger.warning(
                    f"Config files params were unable to get on search: {exc}"
                )
                logger.warning(traceback.format_exc())

            exp = exp_builder.product

            # Get current run data from history
            last_modified_timestamp = exp.created
            completed = exp.completed_jobs if exp.completed_jobs else 0
            total = exp.total_jobs if exp.total_jobs else 0
            submitted = 0
            queuing = 0
            running = 0
            failed = 0
            suspended = 0
            try:
                current_run = (
                    ExperimentHistoryDirector(ExperimentHistoryBuilder(exp.name))
                    .build_reader_experiment_history()
                    .manager.get_experiment_run_dc_with_max_id()
                )
                if (
                    current_run
                    and current_run.total > 0
                    and (
                        current_run.total == total
                        or current_run.modified_timestamp > last_modified_timestamp
                    )
                ):
                    completed = current_run.completed
                    total = current_run.total
                    submitted = current_run.submitted
                    queuing = current_run.queuing
                    running = current_run.running
                    failed = current_run.failed
                    suspended = current_run.suspended
                    last_modified_timestamp = current_run.modified_timestamp
            except Exception as exc:
                logger.warning((f"Exception getting the current run on search: {exc}"))
                logger.warning(traceback.format_exc())

            # Format data
            experiments.append(
                {
                    "id": exp.id,
                    "name": exp.name,
                    "user": exp.user,
                    "description": exp.description,
                    "hpc": exp.hpc,
                    "version": exp.autosubmit_version,
                    "wrapper": exp.wrapper,
                    "modified": exp.modified,
                    "status": exp.status if exp.status else "NOT RUNNING",
                    "completed": completed,
                    "total": total,
                    "submitted": submitted,
                    "queuing": queuing,
                    "running": running,
                    "failed": failed,
                    "suspended": suspended,
                }
            )

        # Response
        response = {
            "experiments": experiments,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_pages": math.ceil(total_rows / page_size) if page_size else 1,
                "page_items": len(experiments),
                "total_items": total_rows,
            },
        }
        return response


@with_log_run_times(logger, "EXPDESC")
@with_auth_token(threshold=ProtectionLevels.WRITEONLY)
def experiment_description_view(expid, user_id: Optional[str] = None):
    """
    Replace the description of the experiment.
    """
    new_description = None
    if request.is_json:
        body_data = request.json
        new_description = body_data.get("description", None)
    return (
        update_experiment_description_owner(expid, new_description, user_id),
        HTTPStatus.OK if user_id else HTTPStatus.UNAUTHORIZED,
    )


@with_log_run_times(logger, "GRAPH4")
@with_auth_token()
def exp_graph_view(expid: str, user_id: Optional[str] = None):
    layout = request.args.get("layout", default="standard")
    grouped = request.args.get("grouped", default="none")
    return v3.get_graph_format(expid, layout, grouped)


@with_log_run_times(logger, "STAT4")
@with_auth_token()
def exp_stats_view(expid: str, user_id: Optional[str] = None):
    filter_period = request.args.get("filter_period", type=int)
    filter_type = request.args.get("filter_type", default="Any")
    return v3.get_experiment_statistics(expid, filter_period, filter_type)
