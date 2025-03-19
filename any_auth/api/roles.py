import asyncio
import logging
import typing

import fastapi

import any_auth.deps.app_state as AppState
import any_auth.deps.auth
from any_auth.backend import BackendClient
from any_auth.deps.auth import depends_active_user
from any_auth.types.pagination import Page
from any_auth.types.role import Permission, Role, RoleCreate, RoleUpdate
from any_auth.types.user import UserInDB

logger = logging.getLogger(__name__)

router = fastapi.APIRouter()


@router.get("/roles", tags=["Roles"])
async def api_list_roles(
    limit: int = fastapi.Query(default=20, ge=1, le=100),
    order: typing.Literal["asc", "desc"] = fastapi.Query(default="desc"),
    after: typing.Text = fastapi.Query(default=""),
    before: typing.Text = fastapi.Query(default=""),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_platform(
            Permission.IAM_ROLES_LIST,
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Page[Role]:
    page_roles = await asyncio.to_thread(
        backend_client.roles.list,
        limit=limit,
        order=order,
        after=after.strip() or None,
        before=before.strip() or None,
    )
    return Page[Role].model_validate(page_roles.model_dump())


@router.post("/roles", tags=["Roles"])
async def api_create_role(
    role_create: RoleCreate = fastapi.Body(..., description="The role to create"),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_platform(
            Permission.IAM_ROLES_CREATE,
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Role:
    role = await asyncio.to_thread(
        backend_client.roles.create,
        role_create,
    )
    return Role.model_validate(role.model_dump())


@router.get("/roles/{role_id}", tags=["Roles"])
async def api_retrieve_role(
    role_id: typing.Text = fastapi.Path(
        ..., description="The ID of the role to retrieve"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_platform(
            Permission.IAM_ROLES_GET,
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Role:
    role_id = role_id.strip()

    if not role_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Role ID is required",
        )

    role_in_db = await asyncio.to_thread(backend_client.roles.retrieve, role_id)

    if not role_in_db:
        logger.debug(f"Role '{role_id}' not found, trying to retrieve by name")
        role_in_db = await asyncio.to_thread(
            backend_client.roles.retrieve_by_name, role_id
        )

    if not role_in_db:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    return Role.model_validate(role_in_db.model_dump())


@router.post("/roles/{role_id}", tags=["Roles"])
async def api_update_role(
    role_id: typing.Text = fastapi.Path(
        ..., description="The ID of the role to update"
    ),
    role_update: RoleUpdate = fastapi.Body(..., description="The role to update"),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_platform(
            Permission.IAM_ROLES_UPDATE,
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Role:
    role_id = role_id.strip()

    if not role_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Role ID is required",
        )

    role_in_db = await asyncio.to_thread(
        backend_client.roles.update,
        role_id,
        role_update,
    )
    return Role.model_validate(role_in_db.model_dump())


@router.delete("/roles/{role_id}", tags=["Roles"])
async def api_delete_role(
    role_id: typing.Text = fastapi.Path(
        ..., description="The ID of the role to delete"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_platform(
            Permission.IAM_ROLES_DELETE,
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    await asyncio.to_thread(backend_client.roles.set_disabled, role_id, disabled=True)
    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)


@router.post("/roles/{role_id}/enable", tags=["Roles"])
async def api_enable_role(
    role_id: typing.Text = fastapi.Path(
        ..., description="The ID of the role to enable"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_platform(
            Permission.IAM_ROLES_UPDATE,
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    await asyncio.to_thread(backend_client.roles.set_disabled, role_id, disabled=False)

    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)
