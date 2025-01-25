import asyncio
import typing

import fastapi

import any_auth.deps.app_state as AppState
from any_auth.backend import BackendClient
from any_auth.deps.auth import depends_active_user
from any_auth.types.pagination import Page
from any_auth.types.project import Project, ProjectCreate, ProjectUpdate
from any_auth.types.user import UserInDB

router = fastapi.APIRouter()


@router.get("/organizations/{organization_id}/projects", tags=["Projects"])
async def api_list_projects(
    organization_id: typing.Text,
    limit: int = fastapi.Query(default=20, ge=1, le=100),
    order: typing.Literal["asc", "desc"] = fastapi.Query(default="desc"),
    after: typing.Text = fastapi.Query(default=""),
    before: typing.Text = fastapi.Query(default=""),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Page[Project]:
    organization_id = organization_id.strip()
    if not organization_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Organization ID is required",
        )

    page_projects = await asyncio.to_thread(
        backend_client.projects.list,
        organization_id=organization_id,
        limit=limit,
        order=order,
        after=after.strip() or None,
        before=before.strip() or None,
    )
    return Page[Project].model_validate(page_projects.model_dump())


@router.post("/organizations/{organization_id}/projects", tags=["Projects"])
async def api_create_project(
    organization_id: typing.Text,
    project_create: ProjectCreate,
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Project:
    organization_id = organization_id.strip()
    if not organization_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Organization ID is required",
        )

    project = await asyncio.to_thread(
        backend_client.projects.create,
        project_create,
        organization_id=organization_id,
        created_by=active_user.id,
    )
    return Project.model_validate(project.model_dump())


@router.get("/projects/{project_id}", tags=["Projects"])
async def api_retrieve_project(
    project_id: typing.Text,
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Project:
    project_id = project_id.strip()

    if not project_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Project ID is required",
        )

    project = await asyncio.to_thread(backend_client.projects.retrieve, project_id)

    if not project:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return Project.model_validate(project.model_dump())


@router.post("/projects/{project_id}", tags=["Projects"])
async def api_update_project(
    project_id: typing.Text,
    project_update: ProjectUpdate,
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Project:
    project_id = project_id.strip()

    if not project_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Project ID is required",
        )

    project = await asyncio.to_thread(
        backend_client.projects.update,
        project_id,
        project_update,
    )
    return Project.model_validate(project.model_dump())


@router.delete("/projects/{project_id}", tags=["Projects"])
async def api_delete_project(
    project_id: typing.Text,
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    await asyncio.to_thread(
        backend_client.projects.set_disabled, project_id, disabled=True
    )
    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)


@router.post("/projects/{project_id}/enable", tags=["Projects"])
async def api_enable_project(
    project_id: typing.Text,
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    await asyncio.to_thread(
        backend_client.projects.set_disabled, project_id, disabled=False
    )
