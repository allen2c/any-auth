# any_auth/api/projs.py
# use RBAC
import asyncio
import logging
import typing

import fastapi

import any_auth.deps.app_state as AppState
import any_auth.deps.auth
from any_auth.backend import BackendClient
from any_auth.deps.auth import depends_active_user
from any_auth.types.pagination import Page
from any_auth.types.project import Project, ProjectCreate, ProjectUpdate
from any_auth.types.role import (
    NA_ROLE_NAME,
    ORG_EDITOR_ROLE_NAME,
    ORG_OWNER_ROLE_NAME,
    ORG_VIEWER_ROLE_NAME,
    PLATFORM_CREATOR_ROLE_NAME,
    PLATFORM_MANAGER_ROLE_NAME,
    Permission,
    Role,
)
from any_auth.types.user import UserInDB

logger = logging.getLogger(__name__)

router = fastapi.APIRouter()


@router.get("/projects", tags=["Projects"])
async def api_list_projects(
    organization_id: typing.Text | None = fastapi.Query(default=None),
    limit: int = fastapi.Query(default=20, ge=1, le=100),
    order: typing.Literal["asc", "desc"] = fastapi.Query(default="desc"),
    after: typing.Text = fastapi.Query(default=""),
    before: typing.Text = fastapi.Query(default=""),
    active_user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_platform(
            Permission.PROJECT_LIST,
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Page[Project]:
    page_projects = await asyncio.to_thread(
        backend_client.projects.list,
        organization_id=organization_id,
        limit=limit,
        order=order,
        after=after.strip() or None,
        before=before.strip() or None,
    )
    return Page[Project].model_validate(page_projects.model_dump())


@router.post("/projects", tags=["Projects"])
async def api_create_project(
    project_create: ProjectCreate = fastapi.Body(
        ..., description="The project to create"
    ),
    active_user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_platform(
            Permission.PROJECT_CREATE,
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Project:
    project = await asyncio.to_thread(
        backend_client.projects.create,
        project_create,
        organization_id=None,
        created_by=active_user_roles[0].id,
    )
    return Project.model_validate(project.model_dump())


@router.get("/projects/{project_id}", tags=["Projects"])
async def api_retrieve_project(
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to retrieve"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    active_user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_project(
            Permission.PROJECT_GET,
        )
    ),
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


@router.put(
    "/projects/{project_id}",
    tags=["Projects"],
)
async def api_update_project(
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to update"
    ),
    project_update: ProjectUpdate = fastapi.Body(
        ..., description="The project to update"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    active_user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_project(
            Permission.PROJECT_UPDATE,
        )
    ),
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


@router.delete(
    "/projects/{project_id}",
    tags=["Projects"],
)
async def api_delete_project(
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to delete"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    active_user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_project(
            Permission.PROJECT_DELETE,
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    await asyncio.to_thread(
        backend_client.projects.set_disabled, project_id, disabled=True
    )
    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)


@router.post(
    "/projects/{project_id}/enable",
    tags=["Projects"],
)
async def api_enable_project(
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to enable"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    active_user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_project(
            Permission.PROJECT_DISABLE,
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    await asyncio.to_thread(
        backend_client.projects.set_disabled, project_id, disabled=False
    )

    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)


@router.get(
    "/projects/{project_id}/roles",
    tags=["Projects"],
)
async def api_list_project_roles(
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to list roles for"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    active_user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_project(
            Permission.PROJECT_GET,
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Page[Role]:
    page_roles = await asyncio.to_thread(
        backend_client.roles.list,
        limit=100,
    )

    excluding_roles = {
        PLATFORM_MANAGER_ROLE_NAME,
        PLATFORM_CREATOR_ROLE_NAME,
        ORG_OWNER_ROLE_NAME,
        ORG_EDITOR_ROLE_NAME,
        ORG_VIEWER_ROLE_NAME,
        NA_ROLE_NAME,
    }

    roles = [role for role in page_roles.data if role.name not in excluding_roles]

    return Page[Role].model_validate(
        {
            "object": "list",
            "data": roles,
            "first_id": roles[0].id if roles else None,
            "last_id": roles[-1].id if roles else None,
            "has_more": False,
        }
    )
