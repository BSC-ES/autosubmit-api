from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from typing import Optional
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
import jwt
import requests
from autosubmit_api import config
from autosubmit_api.auth import ProtectionLevels, auth_token_dependency
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.models.responses import LoginResponse
from autosubmit_api.logger import logger
from autosubmit_api.experiment import utils as Utiles


router = APIRouter()


@router.get("/tokentest", name="Test JWT token")
@router.post("/tokentest", name="Test JWT token")
async def test_token(
    user_id: Optional[str] = Depends(
        auth_token_dependency(threshold=ProtectionLevels.NONE, raise_on_fail=False)
    ),
) -> dict:
    """
    Tests if a token is still valid
    """
    return JSONResponse(
        status_code=(HTTPStatus.OK if user_id else HTTPStatus.UNAUTHORIZED),
        content={
            "isValid": True if user_id else False,
            "message": "Unauthorized" if not user_id else None,
        },
    )


@router.get("/login", name="CAS Login")
async def login(
    ticket: Optional[str] = None,
    env: Optional[str] = None,
    request: Request = None,
) -> LoginResponse:
    APIBasicConfig.read()
    ticket = ticket
    environment = env
    referrer = request.headers.get("Referer")
    is_allowed = False
    for allowed_client in APIBasicConfig.ALLOWED_CLIENTS:
        if referrer and referrer.find(allowed_client) >= 0:
            referrer = allowed_client
            is_allowed = True
    if is_allowed is False:
        return JSONResponse(
            {
                "authenticated": False,
                "user": None,
                "token": None,
                "message": "Your client is not authorized for this operation. The API admin needs to add your URL to the list of allowed clients.",
            },
            status_code=HTTPStatus.UNAUTHORIZED,
        )

    target_service = "{}{}/login".format(referrer, environment)
    if not ticket:
        route_to_request_ticket = "{}?service={}".format(
            config.CAS_LOGIN_URL, target_service
        )
        logger.info("Redirected to: " + str(route_to_request_ticket))
        return RedirectResponse(url=route_to_request_ticket)
    # can be used to target the test environment
    # environment = environment if environment is not None else "autosubmitapp"
    cas_verify_ticket_route = (
        config.CAS_VERIFY_URL + "?service=" + target_service + "&ticket=" + ticket
    )
    response = requests.get(cas_verify_ticket_route)
    user = None
    if response:
        user = Utiles.get_cas_user_from_xml(response.content)
    logger.info("CAS verify ticket response: user %s", user)
    if not user:
        return JSONResponse(
            {
                "authenticated": False,
                "user": None,
                "token": None,
                "message": "Can't verify user.",
            },
            status_code=HTTPStatus.UNAUTHORIZED,
        )
    else:  # Login successful
        payload = {
            "user_id": user,
            "sub": user,
            "iat": int(datetime.now().timestamp()),
            "exp": (
                datetime.now(timezone.utc)
                + timedelta(seconds=config.JWT_EXP_DELTA_SECONDS)
            ),
        }
        jwt_token = jwt.encode(payload, config.JWT_SECRET, config.JWT_ALGORITHM)
        return JSONResponse(
            {
                "authenticated": True,
                "user": user,
                "token": f"Bearer {jwt_token}",
                "message": "Token generated.",
            }
        )
