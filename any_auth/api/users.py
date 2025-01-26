import asyncio
import typing

import fastapi

import any_auth.deps.app_state as AppState
from any_auth.backend import BackendClient
from any_auth.deps.auth import depends_active_user
from any_auth.types.pagination import Page
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
    user_create: UserCreate,
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
    user_id: typing.Text,
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
    user_id: typing.Text,
    user_update: UserUpdate,
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
    user_id: typing.Text,
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    await asyncio.to_thread(backend_client.users.set_disabled, user_id, disabled=True)
    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)


@router.post("/users/{user_id}/enable", tags=["Users"])
async def api_enable_user(
    user_id: typing.Text,
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    await asyncio.to_thread(backend_client.users.set_disabled, user_id, disabled=False)
