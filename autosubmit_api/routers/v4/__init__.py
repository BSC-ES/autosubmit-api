from fastapi import APIRouter, Request

from autosubmit_api.models.responses import RoutesResponse
from autosubmit_api.routers.v4 import auth, experiments, user_settings

router = APIRouter()


@router.get("", name="v4 routes index")
async def v4_root_index(request: Request) -> RoutesResponse:
    """
    Returns routes of this router
    """
    routes_info = [
        {"path": f"{request.url.path}{route.path}", "methods": route.methods}
        for route in router.routes
    ]
    return {"routes": routes_info}


router.include_router(auth.router, prefix="/auth")
router.include_router(experiments.router, prefix="/experiments")
router.include_router(user_settings.router, prefix="/user-settings")