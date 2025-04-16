# any_auth/api/aks.py
# use RBAC
import asyncio
import typing

import fastapi

import any_auth.deps.app_state as AppState
import any_auth.deps.auth
from any_auth.backend import BackendClient
from any_auth.types.api_key import APIKey, APIKeyCreate, APIKeyUpdate
from any_auth.types.pagination import Page
from any_auth.types.role import Permission, Role
from any_auth.types.role_assignment import RoleAssignment
from any_auth.types.user import UserInDB

router = fastapi.APIRouter()


@router.get("/api-keys", tags=["API Keys"])
async def api_list_api_keys(
    limit: int = fastapi.Query(default=20, ge=1, le=100),
    order: typing.Literal["asc", "desc"] = fastapi.Query(default="desc"),
    after: typing.Text = fastapi.Query(default=""),
    before: typing.Text = fastapi.Query(default=""),
    active_user_roles: typing.Tuple[
        UserInDB, typing.List[Role], typing.List[RoleAssignment]
    ] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_platform(
            Permission.API_KEY_LIST,
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Page[APIKey]:
    path_api_keys = await asyncio.to_thread(
        backend_client.api_keys.list,
        limit=limit,
        order=order,
        after=after,
        before=before,
    )

    return Page[APIKey].model_validate_json(path_api_keys.model_dump_json())


@router.post("/api-keys", tags=["API Keys"])
async def api_create_api_key(
    created_by: typing.Text = fastapi.Query(
        ..., description="The ID of the user to create the API key for"
    ),
    resource_id: typing.Text = fastapi.Query(
        ..., description="The ID of the resource to create the API key for"
    ),
    api_key_create: APIKeyCreate = fastapi.Body(
        ..., description="The API key to create"
    ),
    active_user_roles: typing.Tuple[
        UserInDB, typing.List[Role], typing.List[RoleAssignment]
    ] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_platform(
            Permission.API_KEY_CREATE,
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> APIKey:
    created_api_key = await asyncio.to_thread(
        backend_client.api_keys.create,
        api_key_create,
        created_by=created_by,
        resource_id=resource_id,
    )

    return APIKey.model_validate_json(created_api_key.model_dump_json())


@router.get("/api-keys/{api_key_id}", tags=["API Keys"])
async def api_retrieve_api_key(
    api_key_id: typing.Text = fastapi.Path(
        ..., description="The ID of the API key to retrieve"
    ),
    active_user_roles: typing.Tuple[
        UserInDB, typing.List[Role], typing.List[RoleAssignment]
    ] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_platform(
            Permission.API_KEY_GET,
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> APIKey:
    api_key = await asyncio.to_thread(
        backend_client.api_keys.retrieve,
        api_key_id,
    )

    if api_key is None:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    return APIKey.model_validate_json(api_key.model_dump_json())


@router.put("/api-keys/{api_key_id}", tags=["API Keys"])
async def api_update_api_key(
    api_key_id: typing.Text = fastapi.Path(
        ..., description="The ID of the API key to update"
    ),
    api_key_update: APIKeyUpdate = fastapi.Body(
        ..., description="The API key to update"
    ),
    active_user_roles: typing.Tuple[
        UserInDB, typing.List[Role], typing.List[RoleAssignment]
    ] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_platform(
            Permission.API_KEY_UPDATE,
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> APIKey:
    updated_api_key = await asyncio.to_thread(
        backend_client.api_keys.update,
        api_key_id,
        api_key_update,
    )

    return APIKey.model_validate_json(updated_api_key.model_dump_json())


@router.delete("/api-keys/{api_key_id}", tags=["API Keys"])
async def api_delete_api_key(
    api_key_id: typing.Text = fastapi.Path(
        ..., description="The ID of the API key to delete"
    ),
    active_user_roles: typing.Tuple[
        UserInDB, typing.List[Role], typing.List[RoleAssignment]
    ] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_platform(
            Permission.API_KEY_DELETE,
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    await asyncio.to_thread(
        backend_client.api_keys.delete,
        api_key_id,
    )

    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)
