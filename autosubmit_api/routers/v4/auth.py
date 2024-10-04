from datetime import datetime, timedelta
from http import HTTPStatus
from typing import Optional
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
import jwt
from cas import CASClient
import requests
from autosubmit_api import config
from autosubmit_api.auth import ProtectionLevels, auth_token_dependency
from autosubmit_api.auth.utils import validate_client
from autosubmit_api.models.responses import AuthResponse, LoginResponse


router = APIRouter()


@router.get("/verify-token", name="Verify JWT token")
async def verify_token(
    user_id: Optional[str] = Depends(
        auth_token_dependency(threshold=ProtectionLevels.NONE, raise_on_fail=False)
    ),
) -> AuthResponse:
    """
    Verify JWT endpoint.
    """
    return JSONResponse(
        status_code=(HTTPStatus.OK if user_id else HTTPStatus.UNAUTHORIZED),
        content={
            "authenticated": True if user_id else False,
            "user": user_id,
        },
    )


@router.get("/cas/v2/login", name="CAS v2 login")
async def cas_v2_login(
    request: Request, service: Optional[str] = None, ticket: Optional[str] = None
) -> LoginResponse:
    """
    CAS v2 login endpoint.
    """
    if not service:
        service = request.base_url

    is_allowed_service = (service == request.base_url) or validate_client(service)

    if not is_allowed_service:
        return JSONResponse(
            content={
                "authenticated": False,
                "user": None,
                "token": None,
                "message": "Your service is not authorized for this operation. The API admin needs to add your URL to the list of allowed clients.",
            },
            status_code=HTTPStatus.UNAUTHORIZED,
        )

    cas_client = CASClient(
        version=2, service_url=service, server_url=config.CAS_SERVER_URL
    )

    if not ticket:
        # No ticket, the request come from end user, send to CAS login
        cas_login_url = cas_client.get_login_url()
        return RedirectResponse(url=cas_login_url)

    # There is a ticket, the request come from CAS as callback.
    # need call `verify_ticket()` to validate ticket and get user profile.
    user, attributes, pgtiou = cas_client.verify_ticket(ticket)

    if not user:
        return JSONResponse(
            content={
                "authenticated": False,
                "user": None,
                "token": None,
                "message": "Can't verify user",
            },
            status_code=HTTPStatus.UNAUTHORIZED,
        )
    else:  # Login successful
        payload = {
            "user_id": user,
            "sub": user,
            "iat": int(datetime.now().timestamp()),
            "exp": (datetime.now() + timedelta(seconds=config.JWT_EXP_DELTA_SECONDS)),
        }
        jwt_token = jwt.encode(payload, config.JWT_SECRET, config.JWT_ALGORITHM)
        return JSONResponse(
            content={
                "authenticated": True,
                "user": user,
                "token": f"Bearer {jwt_token}",
                "message": "Token generated",
            },
            status_code=HTTPStatus.OK,
        )


@router.get("/oauth2/github/login", name="Github OAuth2 login")
async def github_oauth2_login(code: Optional[str] = None) -> LoginResponse:
    """
    Authenticate and authorize user using a cofigured GitHub Oauth app.
    The authorization in done by verifying users membership to either a Github Team
    or Organization.
    """
    if not code:
        return JSONResponse(
            content={
                "authenticated": False,
                "user": None,
                "token": None,
                "message": "Can't verify user",
            },
            status_code=HTTPStatus.UNAUTHORIZED,
        )

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
        return JSONResponse(
            content={
                "authenticated": False,
                "user": None,
                "token": None,
                "message": "Couldn't find user on GitHub",
            },
            status_code=HTTPStatus.UNAUTHORIZED,
        )

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
            "exp": (datetime.now() + timedelta(seconds=config.JWT_EXP_DELTA_SECONDS)),
        }
        jwt_token = jwt.encode(payload, config.JWT_SECRET, config.JWT_ALGORITHM)
        return JSONResponse(
            content={
                "authenticated": True,
                "user": username,
                "token": f"Bearer {jwt_token}",
                "message": "Token generated",
            },
            status_code=HTTPStatus.OK,
        )
    else:  # UNAUTHORIZED
        return JSONResponse(
            content={
                "authenticated": False,
                "user": None,
                "token": None,
                "message": "User is not member of organization or team",
            },
            status_code=HTTPStatus.UNAUTHORIZED,
        )
