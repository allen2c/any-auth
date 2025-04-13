import asyncio
import logging
import typing

import fastapi
import pydantic

import any_auth.deps.app_state as AppState
from any_auth.backend import BackendClient
from any_auth.deps.auth import depends_active_user
from any_auth.types.organization import Organization
from any_auth.types.pagination import Page
from any_auth.types.project import Project
from any_auth.types.user import User, UserInDB

logger = logging.getLogger(__name__)


class HealthResponse(pydantic.BaseModel):
    status: typing.Text


router = fastapi.APIRouter()


@router.get("/", response_model=dict)
async def root():
    """Root endpoint - simple API health check."""
    return {"message": "Hello World"}


@router.get("/health", response_model=HealthResponse)
async def health(
    status: typing.Text = fastapi.Depends(AppState.depends_status),
) -> HealthResponse:
    """Application health status endpoint."""
    return HealthResponse(status=status)


@router.get("/me", response_model=User)
async def api_me(active_user: UserInDB = fastapi.Depends(depends_active_user)) -> User:
    """Get current authenticated user information."""
    return User.model_validate(active_user.model_dump())


@router.get("/me/organizations", response_model=Page[Organization])
async def api_me_organizations(
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Page[Organization]:
    """Get organizations that the current user belongs to."""
    # Get organization memberships
    organization_members = await asyncio.to_thread(
        backend_client.organization_members.retrieve_by_user_id, active_user.id
    )

    # Extract organization IDs
    organization_ids = [
        member.organization_id
        for member in organization_members
        if member.organization_id
    ]

    if not organization_ids:
        return Page(object="list", data=[], first_id=None, last_id=None, has_more=False)

    # Get organization details
    organizations = await asyncio.to_thread(
        backend_client.organizations.retrieve_by_ids, organization_ids
    )

    return Page(
        object="list",
        data=organizations,
        first_id=organizations[0].id if organizations else None,
        last_id=organizations[-1].id if organizations else None,
        has_more=False,
    )


@router.get("/me/projects", response_model=Page[Project])
async def api_me_projects(
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Page[Project]:
    """Get projects that the current user has access to."""
    # Get project memberships
    project_members = await asyncio.to_thread(
        backend_client.project_members.retrieve_by_user_id, active_user.id
    )

    # Extract project IDs
    project_ids = [member.project_id for member in project_members if member.project_id]

    if not project_ids:
        logger.debug(f"User '{active_user.id}' has no projects")
        return Page(object="list", data=[], first_id=None, last_id=None, has_more=False)

    logger.debug(f"User '{active_user.id}' has {len(project_ids)} projects")

    # Get project details
    projects = await asyncio.to_thread(
        backend_client.projects.retrieve_by_ids, project_ids
    )

    return Page(
        object="list",
        data=projects,
        first_id=projects[0].id if projects else None,
        last_id=projects[-1].id if projects else None,
        has_more=False,
    )
