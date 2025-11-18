from http import HTTPStatus
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from autosubmit_api.auth import ProtectionLevels, auth_token_dependency
from autosubmit_api.models.requests import PreferredUsernameRequest
from autosubmit_api.models.responses import PreferredUsernameResponse
from autosubmit_api.repositories.user_preferences import (
    create_user_preferences_repository,
)


router = APIRouter()


@router.post("/preferred-username", name="Register preferred username from authenticated user")
async def register_preferred_username(
    request: PreferredUsernameRequest,
    user_id: Optional[str] = Depends(
        auth_token_dependency(threshold=ProtectionLevels.NONE, raise_on_fail=True)
    ),
) -> PreferredUsernameResponse:
    """
    Register or update the preferred Linux username for the authenticated user.
    """
    if not user_id:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail="User not authenticated",
        )

    repo = create_user_preferences_repository()
    preferences = repo.upsert_preferred_username(user_id, request.preferred_username)

    return JSONResponse(
        status_code=HTTPStatus.OK,
        content={
            "user_id": preferences.user_id,
            "preferred_username": preferences.preferred_username,
            "created": preferences.created,
            "modified": preferences.modified,
        },
    )


@router.get("/preferred-username", name="Get preferred username for authenticated user")
async def get_preferred_username(
    user_id: Optional[str] = Depends(
        auth_token_dependency(threshold=ProtectionLevels.NONE, raise_on_fail=True)
    ),
) -> PreferredUsernameResponse:
    """
    Get the preferred Linux username for the authenticated user.
    """
    if not user_id:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail="User not authenticated",
        )

    repo = create_user_preferences_repository()
    preferences = repo.get_by_user_id(user_id)

    if preferences is None:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Preferred username not found for this user",
        )

    return JSONResponse(
        status_code=HTTPStatus.OK,
        content={
            "user_id": preferences.user_id,
            "preferred_username": preferences.preferred_username,
            "created": preferences.created,
            "modified": preferences.modified,
        },
    )
