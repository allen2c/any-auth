# any_auth/api/v1/routes.py
import fastapi

from any_auth.api.v1.api_keys.route import router as api_keys_router
from any_auth.api.v1.me.routes import router as me_router
from any_auth.api.v1.oauth import router as oauth_router
from any_auth.api.v1.organizations.route import router as organizations_router
from any_auth.api.v1.proj_aks import router as proj_aks_router
from any_auth.api.v1.proj_aks_ras import router as proj_aks_ras_router
from any_auth.api.v1.proj_invites import router as proj_invites_router
from any_auth.api.v1.proj_mem_ras import router as proj_mem_rs_router
from any_auth.api.v1.proj_mems import router as proj_members_router
from any_auth.api.v1.projs import router as projects_router
from any_auth.api.v1.ras import router as role_assignments_router
from any_auth.api.v1.roles import router as roles_router
from any_auth.api.v1.users import router as users_router

router = fastapi.APIRouter(prefix="/v1")

router.include_router(oauth_router)
router.include_router(me_router)
router.include_router(users_router)
router.include_router(api_keys_router)
router.include_router(organizations_router)
router.include_router(projects_router)
router.include_router(proj_members_router)
router.include_router(proj_mem_rs_router)
router.include_router(proj_aks_router)
router.include_router(proj_aks_ras_router)
router.include_router(proj_invites_router)
router.include_router(roles_router)
router.include_router(role_assignments_router)
