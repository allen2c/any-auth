import fastapi

from any_auth.api.auth.route import router as auth_router
from any_auth.api.health import router as health_router
from any_auth.api.oauth2 import router as oauth2_router
from any_auth.api.oidc import router as oidc_router
from any_auth.api.v1.route import router as v1_router

router = fastapi.APIRouter()

router.include_router(auth_router)
router.include_router(health_router)
router.include_router(oauth2_router)
router.include_router(oidc_router)
router.include_router(v1_router)
