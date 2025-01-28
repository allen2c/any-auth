import asyncio
import json
import typing

import fastapi
from pydantic.json import pydantic_encoder

import any_auth.deps.app_state as AppState
import any_auth.deps.permission
from any_auth.backend import BackendClient
from any_auth.deps.auth import depends_active_user
from any_auth.types.organization import Organization
from any_auth.types.pagination import Page
from any_auth.types.project import Project
from any_auth.types.role import Permission, Role
from any_auth.types.role_assignment import RoleAssignment
from any_auth.types.user import User, UserCreate, UserInDB, UserUpdate

router = fastapi.APIRouter()


@router.get("/users", tags=["Users"])
async def api_list_users(
    limit: int = fastapi.Query(default=20, ge=1, le=100),
    order: typing.Literal["asc", "desc"] = fastapi.Query(default="desc"),
    after: typing.Text = fastapi.Query(default=""),
    before: typing.Text = fastapi.Query(default=""),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.USER_LIST, resource_id_source="platform"
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Page[User]:
    page_users = await asyncio.to_thread(
        backend_client.users.list,
        limit=limit,
        order=order,
        after=after.strip() or None,
        before=before.strip() or None,
    )
    return Page[User].model_validate(page_users.model_dump())


@router.post("/users", tags=["Users"])
async def api_create_user(
    user_create: UserCreate = fastapi.Body(..., description="The user to create"),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.USER_CREATE, resource_id_source="platform"
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> User:
    user_in_db = await asyncio.to_thread(
        backend_client.users.create,
        user_create,
    )
    return User.model_validate(user_in_db.model_dump())


@router.get("/users/{user_id}", tags=["Users"])
async def api_retrieve_user(
    user_id: typing.Text = fastapi.Path(
        ..., description="The ID of the user to retrieve"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.USER_GET, resource_id_source="platform"
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> User:
    user_id = user_id.strip()

    if not user_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="User ID is required",
        )

    user_in_db = await asyncio.to_thread(backend_client.users.retrieve, user_id)

    if not user_in_db:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return User.model_validate(user_in_db.model_dump())


@router.post("/users/{user_id}", tags=["Users"])
async def api_update_user(
    user_id: typing.Text = fastapi.Path(
        ..., description="The ID of the user to update"
    ),
    user_update: UserUpdate = fastapi.Body(..., description="The user to update"),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.USER_UPDATE, resource_id_source="platform"
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> User:
    user_id = user_id.strip()

    if not user_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="User ID is required",
        )

    user_in_db = await asyncio.to_thread(
        backend_client.users.update,
        user_id,
        user_update,
    )
    return User.model_validate(user_in_db.model_dump())


@router.delete("/users/{user_id}", tags=["Users"])
async def api_delete_user(
    user_id: typing.Text = fastapi.Path(
        ..., description="The ID of the user to delete"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.USER_DELETE, resource_id_source="platform"
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    await asyncio.to_thread(backend_client.users.set_disabled, user_id, disabled=True)
    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)


@router.post("/users/{user_id}/enable", tags=["Users"])
async def api_enable_user(
    user_id: typing.Text = fastapi.Path(
        ..., description="The ID of the user to enable"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.USER_DISABLE, resource_id_source="platform"
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    await asyncio.to_thread(backend_client.users.set_disabled, user_id, disabled=False)

    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)


@router.get("/users/{user_id}/role-assignments", tags=["Users"])
async def api_list_user_role_assignments(
    user_id: typing.Text = fastapi.Path(
        ..., description="The ID of the user to retrieve role assignments for"
    ),
    resource_id: typing.Text = fastapi.Query(
        default="",
        description="The ID of the resource to retrieve role assignments for",
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.IAM_GET_POLICY, resource_id_source="platform"
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Page[RoleAssignment]:
    resource_id = resource_id.strip()

    if not resource_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Resource ID is required",
        )

    role_assignments = await asyncio.to_thread(
        backend_client.role_assignments.retrieve_by_user_id,
        user_id,
        resource_id=resource_id,
    )
    return Page[RoleAssignment].model_validate(
        {
            "object": "list",
            "data": json.loads(json.dumps(role_assignments, default=pydantic_encoder)),
            "first_id": role_assignments[0].id if role_assignments else None,
            "last_id": role_assignments[-1].id if role_assignments else None,
            "has_more": False,
        }
    )


@router.get("/users/{user_id}/roles", tags=["Users"])
async def api_list_user_roles(
    user_id: typing.Text = fastapi.Path(
        ..., description="The ID of the user to retrieve roles for"
    ),
    resource_id: typing.Text = fastapi.Query(
        default="", description="The ID of the resource to retrieve roles for"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.IAM_ROLES_LIST, resource_id_source="platform"
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Page[Role]:
    resource_id = resource_id.strip()

    if not resource_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Resource ID is required",
        )

    roles = await asyncio.to_thread(
        backend_client.roles.retrieve_by_user_id,
        user_id,
        resource_id=resource_id,
    )
    return Page[Role].model_validate(
        {
            "object": "list",
            "data": json.loads(json.dumps(roles, default=pydantic_encoder)),
            "first_id": roles[0].id if roles else None,
            "last_id": roles[-1].id if roles else None,
            "has_more": False,
        }
    )


@router.get("/users/{user_id}/organizations", tags=["Users"])
async def api_list_user_organizations(
    user_id: typing.Text = fastapi.Path(
        ..., description="The ID of the user to retrieve organizations for"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.ORG_LIST, resource_id_source="platform"
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Page[Organization]:
    org_members = await asyncio.to_thread(
        backend_client.organization_members.retrieve_by_user_id,
        user_id,
    )
    org_ids = [
        org_member.organization_id
        for org_member in org_members
        if org_member.organization_id
    ]
    orgs = await asyncio.to_thread(
        backend_client.organizations.retrieve_by_ids,
        org_ids,
    )
    orgs.sort(key=lambda org: org.id)
    return Page[Organization].model_validate(
        {
            "object": "list",
            "data": orgs,
            "first_id": orgs[0].id if orgs else None,
            "last_id": orgs[-1].id if orgs else None,
            "has_more": False,
        }
    )


@router.get("/users/{user_id}/projects", tags=["Users"])
async def api_list_user_projects(
    user_id: typing.Text = fastapi.Path(
        ..., description="The ID of the user to retrieve projects for"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.PROJECT_LIST, resource_id_source="platform"
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Page[Project]:
    project_members = await asyncio.to_thread(
        backend_client.project_members.retrieve_by_user_id,
        user_id,
    )
    project_ids = [
        project_member.project_id
        for project_member in project_members
        if project_member.project_id
    ]
    projects = await asyncio.to_thread(
        backend_client.projects.retrieve_by_ids, project_ids
    )
    projects.sort(key=lambda project: project.id)
    return Page[Project].model_validate(
        {
            "object": "list",
            "data": projects,
            "first_id": projects[0].id if projects else None,
            "last_id": projects[-1].id if projects else None,
            "has_more": False,
        }
    )
