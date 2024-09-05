from collections import deque
from datetime import datetime, timedelta
from enum import Enum
from http import HTTPStatus
import math
import traceback
from typing import Dict, List, Optional
from flask import redirect, request
from flask.views import MethodView
import jwt
import requests
from autosubmit_api.auth import ProtectionLevels, with_auth_token
from autosubmit_api.auth.utils import validate_client
from autosubmit_api.builders.experiment_builder import ExperimentBuilder
from autosubmit_api.builders.experiment_history_builder import (
    ExperimentHistoryBuilder,
    ExperimentHistoryDirector,
)
from autosubmit_api.common.utils import Status
from autosubmit_api.database import tables
from autosubmit_api.database.common import (
    create_main_db_conn,
    execute_with_limit_offset,
)
from autosubmit_api.database.queries import generate_query_listexp_extended
from autosubmit_api.logger import logger, with_log_run_times
from cas import CASClient
from autosubmit_api import config
from autosubmit_api.persistance.job_package_reader import JobPackageReader
from autosubmit_api.persistance.pkl_reader import PklReader


PAGINATION_LIMIT_DEFAULT = 12


class CASV2Login(MethodView):
    decorators = [with_log_run_times(logger, "CASV2LOGIN")]

    def get(self):
        ticket = request.args.get("ticket")
        service = request.args.get("service", request.base_url)

        is_allowed_service = (service == request.base_url) or validate_client(service)

        if not is_allowed_service:
            return {
                "authenticated": False,
                "user": None,
                "token": None,
                "message": "Your service is not authorized for this operation. The API admin needs to add your URL to the list of allowed clients.",
            }, HTTPStatus.UNAUTHORIZED

        cas_client = CASClient(
            version=2, service_url=service, server_url=config.CAS_SERVER_URL
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
                "exp": (
                    datetime.now() + timedelta(seconds=config.JWT_EXP_DELTA_SECONDS)
                ),
            }
            jwt_token = jwt.encode(payload, config.JWT_SECRET, config.JWT_ALGORITHM)
            return {
                "authenticated": True,
                "user": user,
                "token": jwt_token,
                "message": "Token generated",
            }, HTTPStatus.OK


class GithubOauth2Login(MethodView):
    decorators = [with_log_run_times(logger, "GHOAUTH2LOGIN")]

    def get(self):
        """
        Authenticate and authorize user using a cofigured GitHub Oauth app.
        The authorization in done by verifying users membership to either a Github Team
        or Organization.
        """

        code = request.args.get("code")

        if not code:
            return {
                "authenticated": False,
                "user": None,
                "token": None,
                "message": "Can't verify user",
            }, HTTPStatus.UNAUTHORIZED

        resp_obj: dict = requests.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": config.GITHUB_OAUTH_CLIENT_ID,
                "client_secret": config.GITHUB_OAUTH_CLIENT_SECRET,
                "code": code,
            },
            headers={"Accept": "application/json"},
        ).json()
        access_token = resp_obj.get("access_token")

        user_info: dict = requests.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"},
        ).json()
        username = user_info.get("login")

        if not username:
            return {
                "authenticated": False,
                "user": None,
                "token": None,
                "message": "Couldn't find user on GitHub",
            }, HTTPStatus.UNAUTHORIZED

        # Whitelist organization team
        if (
            config.GITHUB_OAUTH_WHITELIST_ORGANIZATION
            and config.GITHUB_OAUTH_WHITELIST_TEAM
        ):
            org_resp = requests.get(
                f"https://api.github.com/orgs/{config.GITHUB_OAUTH_WHITELIST_ORGANIZATION}/teams/{config.GITHUB_OAUTH_WHITELIST_TEAM}/memberships/{username}",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            membership: dict = org_resp.json()
            is_member = (
                org_resp.status_code == 200 and membership.get("state") == "active"
            )  # https://docs.github.com/en/rest/teams/members?apiVersion=2022-11-28#get-team-membership-for-a-user
        elif (
            config.GITHUB_OAUTH_WHITELIST_ORGANIZATION
        ):  # Whitelist all organization (no team)
            org_resp = requests.get(
                f"https://api.github.com/orgs/{config.GITHUB_OAUTH_WHITELIST_ORGANIZATION}/members/{username}",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            is_member = (
                org_resp.status_code == 204
            )  # https://docs.github.com/en/rest/orgs/members?apiVersion=2022-11-28#check-organization-membership-for-a-user
        else:  # No authorization check
            is_member = True

        # Login successful
        if is_member:
            payload = {
                "user_id": username,
                "sub": username,
                "iat": int(datetime.now().timestamp()),
                "exp": (
                    datetime.now() + timedelta(seconds=config.JWT_EXP_DELTA_SECONDS)
                ),
            }
            jwt_token = jwt.encode(payload, config.JWT_SECRET, config.JWT_ALGORITHM)
            return {
                "authenticated": True,
                "user": username,
                "token": jwt_token,
                "message": "Token generated",
            }, HTTPStatus.OK
        else:  # UNAUTHORIZED
            return {
                "authenticated": False,
                "user": None,
                "token": None,
                "message": "User is not member of organization or team",
            }, HTTPStatus.UNAUTHORIZED


class AuthJWTVerify(MethodView):
    decorators = [
        with_auth_token(threshold=ProtectionLevels.NONE, response_on_fail=False),
        with_log_run_times(logger, "JWTVRF"),
    ]

    def get(self, user_id: Optional[str] = None):
        """
        Verify JWT endpoint.
        """
        return {
            "authenticated": True if user_id else False,
            "user": user_id,
        }, (HTTPStatus.OK if user_id else HTTPStatus.UNAUTHORIZED)


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
        autosubmit_version = request.args.get("autosubmit_version")

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
        except Exception:
            return {"error": {"message": "Invalid params"}}, HTTPStatus.BAD_REQUEST

        # Query
        statement = generate_query_listexp_extended(
            query=query,
            only_active=only_active,
            owner=owner,
            exp_type=exp_type,
            autosubmit_version=autosubmit_version,
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
            completed = 0
            total = 0
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
                if current_run and current_run.total > 0:
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
                    # "wrapper": exp.wrapper,
                    "created": exp.created,
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


class ExperimentDetailView(MethodView):
    decorators = [with_auth_token(), with_log_run_times(logger, "EXPDETAIL")]

    def get(self, expid: str, user_id: Optional[str] = None):
        """
        Get details of an experiment
        """
        exp_builder = ExperimentBuilder()
        exp_builder.produce_base(expid)
        return exp_builder.product.model_dump(include=tables.experiment_table.c.keys())


class ExperimentJobsViewOptEnum(str, Enum):
    QUICK = "quick"
    BASE = "base"


class ExperimentJobsView(MethodView):
    decorators = [with_auth_token(), with_log_run_times(logger, "EXPJOBS")]

    def get(self, expid: str, user_id: Optional[str] = None):
        """
        Get the experiment jobs from pickle file.
        BASE view returns base content of the pkl file.
        QUICK view returns a reduced payload with just the name and status of the jobs.
        """
        view = request.args.get(
            "view", type=str, default=ExperimentJobsViewOptEnum.BASE
        )

        # Read the pkl
        try:
            current_content = PklReader(expid).parse_job_list()
        except Exception as exc:
            error_message = "Error while reading the job list"
            logger.error(error_message + f": {exc}")
            logger.error(traceback.print_exc())
            return {
                "error": {"message": error_message}
            }, HTTPStatus.INTERNAL_SERVER_ERROR

        pkl_jobs = deque()
        for job_item in current_content:
            resp_job = {
                "name": job_item.name,
                "status": Status.VALUE_TO_KEY.get(job_item.status, Status.UNKNOWN),
            }

            if view == ExperimentJobsViewOptEnum.BASE:
                resp_job = {
                    **resp_job,
                    "priority": job_item.priority,
                    "section": job_item.section,
                    "date": (
                        job_item.date.date().isoformat()
                        if isinstance(job_item.date, datetime)
                        else None
                    ),
                    "member": job_item.member,
                    "chunk": job_item.chunk,
                    "out_path_local": job_item.out_path_local,
                    "err_path_local": job_item.err_path_local,
                    "out_path_remote": job_item.out_path_remote,
                    "err_path_remote": job_item.err_path_remote,
                }

            if job_item.status in [Status.COMPLETED, Status.WAITING, Status.READY]:
                pkl_jobs.append(resp_job)
            else:
                pkl_jobs.appendleft(resp_job)

        return {"jobs": list(pkl_jobs)}, HTTPStatus.OK


class ExperimentWrappersView(MethodView):
    decorators = [with_auth_token(), with_log_run_times(logger, "WRAPPERS")]

    def get(self, expid: str, user_id: Optional[str] = None):

        job_package_reader = JobPackageReader(expid)
        job_package_reader.read()

        wrappers_dict: Dict[str, List[str]] = job_package_reader.package_to_jobs

        wrappers = []
        for key, val in wrappers_dict.items():
            wrappers.append({"wrapper_name": key, "job_names": val})

        logger.debug(wrappers)
        return {"wrappers": wrappers}
