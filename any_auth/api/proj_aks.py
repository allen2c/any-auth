import asyncio
import json
import logging
import typing

import fastapi

import any_auth.deps.app_state as AppState
import any_auth.deps.auth
from any_auth.backend import BackendClient
from any_auth.deps.auth import depends_active_user
from any_auth.types.api_key import APIKey, APIKeyCreate, APIKeyUpdate
from any_auth.types.pagination import Page
from any_auth.types.role import Permission, Role
from any_auth.types.user import UserInDB

logger = logging.getLogger(__name__)

router = fastapi.APIRouter()


@router.get(
    "/projects/{project_id}/api-keys",
    tags=["Projects"],
)
async def api_list_project_api_keys(
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to retrieve API keys for"
    ),
    limit: int = fastapi.Query(default=20, ge=1, le=100),
    order: typing.Literal["asc", "desc"] = fastapi.Query(default="desc"),
    after: typing.Text = fastapi.Query(default=""),
    before: typing.Text = fastapi.Query(default=""),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    active_user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_project(
            Permission.API_KEY_LIST,
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Page[APIKey]:
    page_project_api_keys = await asyncio.to_thread(
        backend_client.api_keys.list,
        resource_id=project_id,
        limit=limit,
        order=order,
        after=after,
        before=before,
    )

    return Page[APIKey].model_validate_json(page_project_api_keys.model_dump_json())


@router.post(
    "/projects/{project_id}/api-keys",
    tags=["Projects"],
)
async def api_create_project_api_key(
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to create a member for"
    ),
    api_key_create: APIKeyCreate = fastapi.Body(
        ..., description="The API key to create"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    active_user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_project(
            Permission.API_KEY_CREATE,
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> typing.Dict:
    plain_key = APIKey.generate_plain_api_key()
    created_api_key = await asyncio.to_thread(
        backend_client.api_keys.create,
        api_key_create,
        created_by=active_user.id,
        resource_id=project_id,
        plain_key=plain_key,
    )

    response_data = json.loads(created_api_key.model_dump_json())
    response_data["api_key"] = plain_key
    return response_data


@router.get(
    "/projects/{project_id}/api-keys/{api_key_id}",
    tags=["Projects"],
)
async def api_retrieve_project_api_key(
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to retrieve an API key for"
    ),
    api_key_id: typing.Text = fastapi.Path(
        ..., description="The ID of the API key to retrieve"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    active_user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_project(
            Permission.API_KEY_GET,
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> APIKey:
    project_api_key = await asyncio.to_thread(
        backend_client.api_keys.retrieve,
        api_key_id=api_key_id,
    )

    if not project_api_key:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    if project_api_key.resource_id != project_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    return APIKey.model_validate_json(project_api_key.model_dump_json())


@router.put(
    "/projects/{project_id}/api-keys/{api_key_id}",
    tags=["Projects"],
)
async def api_update_project_api_key(
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to update an API key for"
    ),
    api_key_id: typing.Text = fastapi.Path(
        ..., description="The ID of the API key to update"
    ),
    api_key_update: APIKeyUpdate = fastapi.Body(
        ..., description="The API key to update"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    active_user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_project(
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


@router.delete(
    "/projects/{project_id}/api-keys/{api_key_id}",
    tags=["Projects"],
)
async def api_delete_project_api_key(
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to delete an API key for"
    ),
    api_key_id: typing.Text = fastapi.Path(
        ..., description="The ID of the API key to delete"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    active_user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_project(
            Permission.API_KEY_DELETE,
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    target_project_api_key = await asyncio.to_thread(
        backend_client.api_keys.retrieve,
        api_key_id=api_key_id,
    )
    if not target_project_api_key:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )
    if target_project_api_key.resource_id != project_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    await asyncio.to_thread(
        backend_client.api_keys.delete,
        api_key_id,
    )

    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)


@router.get(
    "/projects/{project_id}/api-keys/{api_key_id}/roles",
    tags=["Projects"],
)
async def api_retrieve_project_api_key_roles(
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to retrieve an API key for"
    ),
    api_key_id: typing.Text = fastapi.Path(
        ..., description="The ID of the API key to retrieve"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    active_user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_project(
            Permission.API_KEY_GET,
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Page[Role]:
    project_api_key = await asyncio.to_thread(
        backend_client.api_keys.retrieve,
        api_key_id=api_key_id,
    )

    if not project_api_key:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    role_assignments = await asyncio.to_thread(
        backend_client.role_assignments.retrieve_by_target_id,
        target_id=project_api_key.id,
        resource_id=project_id,
    )

    if len(role_assignments) == 0:
        return Page[Role].model_validate(
            {
                "object": "list",
                "data": [],
                "first_id": None,
                "last_id": None,
                "has_more": False,
            }
        )

    roles = await asyncio.to_thread(
        backend_client.roles.retrieve_by_ids,
        [assignment.role_id for assignment in role_assignments],
    )
    return Page[Role].model_validate(
        {
            "object": "list",
            "data": roles,
            "first_id": roles[0].id if roles else None,
            "last_id": roles[-1].id if roles else None,
            "has_more": False,
        }
    )
