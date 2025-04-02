import asyncio
import typing

import fastapi

import any_auth.deps.app_state as AppState
import any_auth.deps.auth
from any_auth.backend._client import BackendClient
from any_auth.deps.auth import depends_active_user
from any_auth.types.oauth_client import OAuthClient, OAuthClientCreate
from any_auth.types.pagination import Page
from any_auth.types.role import Permission, Role
from any_auth.types.role_assignment import RoleAssignment
from any_auth.types.user import UserInDB

router = fastapi.APIRouter(tags=["OAuth Clients"])


@router.post("/oauth/clients")
async def api_create_oauth_client(
    oauth_client_create: OAuthClientCreate = fastapi.Body(...),
    active_user: UserInDB = fastapi.Depends(depends_active_user),  # Required
    allowed_active_user_roles: typing.Tuple[
        UserInDB, typing.List[Role], typing.List[RoleAssignment]
    ] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_platform(
            Permission.IAM_SET_POLICY,
        )
    ),  # Required
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> OAuthClient:
    oauth_client = await asyncio.to_thread(
        backend_client.oauth_clients.create, oauth_client_create
    )
    return OAuthClient.model_validate_json(oauth_client.model_dump_json())


@router.get("/oauth/clients")
async def api_list_oauth_clients(
    project_id: str = fastapi.Query(...),
    active_user: UserInDB = fastapi.Depends(depends_active_user),  # Required
    allowed_active_user_roles: typing.Tuple[
        UserInDB, typing.List[Role], typing.List[RoleAssignment]
    ] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_platform(
            Permission.IAM_GET_POLICY,
        )
    ),  # Required
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Page[OAuthClient]:
    page_oauth_clients = await asyncio.to_thread(
        backend_client.oauth_clients.list, project_id=project_id
    )
    return Page[OAuthClient].model_validate_json(page_oauth_clients.model_dump_json())


@router.get("/oauth/clients/{client_id}")
async def api_retrieve_oauth_client(
    client_id: str = fastapi.Path(...),
    active_user: UserInDB = fastapi.Depends(depends_active_user),  # Required
    allowed_active_user_roles: typing.Tuple[
        UserInDB, typing.List[Role], typing.List[RoleAssignment]
    ] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_platform(
            Permission.IAM_GET_POLICY,
        )
    ),  # Required
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> OAuthClient:
    oauth_client = await asyncio.to_thread(
        backend_client.oauth_clients.retrieve, client_id
    )
    if oauth_client is None:
        raise fastapi.HTTPException(status_code=404, detail="OAuth client not found")
    return OAuthClient.model_validate_json(oauth_client.model_dump_json())


@router.patch("/oauth/clients/{client_id}/disable")
async def api_disable_oauth_client(
    client_id: str = fastapi.Path(...),
    active_user: UserInDB = fastapi.Depends(depends_active_user),  # Required
    allowed_active_user_roles: typing.Tuple[
        UserInDB, typing.List[Role], typing.List[RoleAssignment]
    ] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_platform(
            Permission.IAM_SET_POLICY,
        )
    ),  # Required
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> OAuthClient:
    oauth_client = await asyncio.to_thread(
        backend_client.oauth_clients.set_disabled, client_id, disabled=True
    )
    return OAuthClient.model_validate_json(oauth_client.model_dump_json())


@router.patch("/oauth/clients/{client_id}/enable")
async def api_enable_oauth_client(
    client_id: str = fastapi.Path(...),
    active_user: UserInDB = fastapi.Depends(depends_active_user),  # Required
    allowed_active_user_roles: typing.Tuple[
        UserInDB, typing.List[Role], typing.List[RoleAssignment]
    ] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_platform(
            Permission.IAM_SET_POLICY,
        )
    ),  # Required
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> OAuthClient:
    oauth_client = await asyncio.to_thread(
        backend_client.oauth_clients.set_disabled, client_id, disabled=False
    )
    return OAuthClient.model_validate_json(oauth_client.model_dump_json())
