from fastapi import APIRouter

from autosubmit_api.routers.v3 import experiments, auth

router = APIRouter()

router.include_router(experiments.router)
router.include_router(auth.router)
