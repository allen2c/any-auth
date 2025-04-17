# any_auth/api/v1/routes.py
import fastapi

from any_auth.api.v1.api_keys.route import router as api_keys_router
from any_auth.api.v1.me.routes import router as me_router
from any_auth.api.v1.oauth import router as oauth_router
from any_auth.api.v1.organizations.route import router as organizations_router
from any_auth.api.v1.projects.route import router as projects_router
from any_auth.api.v1.role_assignments.route import router as role_assignments_router
from any_auth.api.v1.roles.route import router as roles_router
from any_auth.api.v1.users.route import router as users_router

router = fastapi.APIRouter(prefix="/v1")

router.include_router(oauth_router)
router.include_router(me_router)
router.include_router(users_router)
router.include_router(api_keys_router)
router.include_router(organizations_router)
router.include_router(projects_router)
router.include_router(roles_router)
router.include_router(role_assignments_router)
