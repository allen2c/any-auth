import asyncio
import json
import typing

import fastapi
from pydantic.json import pydantic_encoder

import any_auth.deps.app_state as AppState
from any_auth.backend import BackendClient
from any_auth.deps.auth import depends_active_user
from any_auth.types.pagination import Page
from any_auth.types.role import Role
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
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    await asyncio.to_thread(backend_client.users.set_disabled, user_id, disabled=False)

    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)


@router.get("/users/{user_id}/role-assignments", tags=["Users"])
async def api_list_user_role_assignments(
    user_id: typing.Text = fastapi.Path(
        ..., description="The ID of the user to retrieve role assignments for"
    ),
    project_id: typing.Text = fastapi.Query(
        default="", description="The ID of the project to retrieve role assignments for"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Page[RoleAssignment]:
    role_assignments = await asyncio.to_thread(
        backend_client.role_assignments.retrieve_by_user_id,
        user_id,
        project_id=project_id,
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
    project_id: typing.Text = fastapi.Query(
        default="", description="The ID of the project to retrieve roles for"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Page[Role]:
    roles = await asyncio.to_thread(
        backend_client.roles.retrieve_by_user_id,
        user_id,
        project_id=project_id,
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
