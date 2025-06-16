from fastapi import APIRouter
from autosubmit_api import __version__ as APIVersion
from autosubmit_api.routers import v4, v3, v4alpha

router = APIRouter()


@router.get("/", name="Home")
async def home():
    return {"name": "Autosubmit API", "version": APIVersion}


router.include_router(v4.router, prefix="/v4", tags=["v4"])
router.include_router(v3.router, prefix="/v3", tags=["v3"])
router.include_router(v4alpha.router, prefix="/v4alpha", tags=["v4alpha"])