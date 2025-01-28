import asyncio
import logging
import typing

import fastapi
import pydantic

import any_auth.deps.app_state
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


@router.get("/")
async def root():
    return {"message": "Hello World"}


@router.get("/health")
async def health(
    status: typing.Text = fastapi.Depends(any_auth.deps.app_state.depends_status),
) -> HealthResponse:
    return HealthResponse(status=status)


@router.get("/me")
async def api_me(active_user: UserInDB = fastapi.Depends(depends_active_user)) -> User:
    return active_user


@router.get("/me/organizations")
async def api_me_organizations(
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Page[Organization]:
    organization_members = await asyncio.to_thread(
        backend_client.organization_members.retrieve_by_user_id, active_user.id
    )
    _organization_ids = [
        organization_member.organization_id
        for organization_member in organization_members
        if organization_member.organization_id
    ]
    if not _organization_ids:
        return Page(object="list", data=[], first_id=None, last_id=None, has_more=False)

    organizations = await asyncio.to_thread(
        backend_client.organizations.retrieve_by_ids, _organization_ids
    )
    return Page(
        object="list",
        data=organizations,
        first_id=organizations[0].id if organizations else None,
        last_id=organizations[-1].id if organizations else None,
        has_more=False,
    )


@router.get("/me/projects")
async def api_me_projects(
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Page[Project]:
    project_members = await asyncio.to_thread(
        backend_client.project_members.retrieve_by_user_id, active_user.id
    )
    _projects_ids = [
        project_member.project_id
        for project_member in project_members
        if project_member.project_id
    ]
    if not _projects_ids:
        return Page(object="list", data=[], first_id=None, last_id=None, has_more=False)

    projects = await asyncio.to_thread(
        backend_client.projects.retrieve_by_ids, _projects_ids
    )

    return Page(
        object="list",
        data=projects,
        first_id=projects[0].id if projects else None,
        last_id=projects[-1].id if projects else None,
        has_more=False,
    )
