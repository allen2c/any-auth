# any_auth/api/v1/users/route.py
# use RBAC
import asyncio
import logging
import typing

import fastapi
from str_or_none import str_or_none

import any_auth.deps.app_state as AppState
import any_auth.deps.auth
from any_auth.backend import BackendClient
from any_auth.deps.auth import depends_active_user, deps_oauth_client_credentials
from any_auth.types.oauth_client import OAuthClient
from any_auth.types.organization import Organization
from any_auth.types.pagination import Page
from any_auth.types.project import Project
from any_auth.types.role import Permission, Role
from any_auth.types.user import User, UserCreate, UserInDB, UserUpdate

logger = logging.getLogger(__name__)

router = fastapi.APIRouter()


async def depends_target_user(
    user_id: typing.Text = fastapi.Path(
        ..., description="The ID of the user to retrieve"
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> UserInDB:
    might_user_id = str_or_none(user_id)
    if might_user_id is None:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="User ID is required",
        )
    target_user_id = might_user_id

    target_user_in_db = await asyncio.to_thread(
        backend_client.users.retrieve, target_user_id
    )

    if target_user_in_db is None:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return target_user_in_db


@router.post("/users/register", tags=["Users"])
async def api_register_user(
    user_create: UserCreate = fastapi.Body(
        ..., description="User registration details"
    ),
    oauth_client: OAuthClient = fastapi.Depends(deps_oauth_client_credentials),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> User:
    """
    Register a new user. Requires USER_CREATE permission.
    This endpoint replaces the public registration endpoint with a permission-controlled version.
    """  # noqa: E501

    assert oauth_client, "Valid OAuth client is required"

    logger.info(f"Attempting to register user with email: {user_create.email}")

    # 1. Check if email already exists
    existing_by_email = await asyncio.to_thread(
        backend_client.users.retrieve_by_email, user_create.email
    )
    if existing_by_email:
        logger.warning(
            f"Registration attempt failed: Email '{user_create.email}' already exists."
        )
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_409_CONFLICT,
            detail="A user with this email or username already exists.",
        )

    # 2. Check if username already exists
    existing_by_username = await asyncio.to_thread(
        backend_client.users.retrieve_by_username, user_create.username
    )
    if existing_by_username:
        logger.warning(
            f"Registration attempt failed: Username '{user_create.username}' "
            + "already exists."
        )
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_409_CONFLICT,
            detail="A user with this email or username already exists.",
        )

    # Create User
    try:
        # Create the user in the database
        user_in_db = await asyncio.to_thread(
            backend_client.users.create,
            user_create,
        )
        logger.info(
            f"Successfully registered user {user_in_db.username} "
            + f"({user_in_db.id}) via protected endpoint."
        )

    except fastapi.HTTPException as e:
        raise e

    except Exception as e:
        logger.exception(e)
        logger.exception(
            f"Error during user registration for email {user_create.email}: {e}"
        )
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during registration.",
        )

    # Return the publicly viewable User model, not UserInDB which has the hash
    return User.model_validate(user_in_db.model_dump())


@router.get("/users/check", tags=["Users"])
async def api_check_user_exists(
    email: typing.Text = fastapi.Query(default="", description="Email to check"),
    username: typing.Text = fastapi.Query(default="", description="Username to check"),
    oauth_client: OAuthClient = fastapi.Depends(deps_oauth_client_credentials),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> typing.Dict[typing.Text, bool]:
    assert oauth_client, "Valid OAuth client is required"

    email, username = email.strip(), username.strip()
    if not email and not username:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Either email or username is required",
        )

    if email:
        might_exists_user = await asyncio.to_thread(
            backend_client.users.retrieve_by_email,
            email,
        )
        if might_exists_user is not None:
            return {"exists": True}

    if username:
        might_exists_user = await asyncio.to_thread(
            backend_client.users.retrieve_by_username,
            username,
        )
        if might_exists_user is not None:
            return {"exists": True}

    return {"exists": False}


@router.get("/users", tags=["Users"])
async def api_list_users(
    limit: int = fastapi.Query(default=20, ge=1, le=100),
    order: typing.Literal["asc", "desc"] = fastapi.Query(default="desc"),
    after: typing.Text = fastapi.Query(default=""),
    before: typing.Text = fastapi.Query(default=""),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_platform(Permission.USER_LIST)
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
        any_auth.deps.auth.depends_permissions_for_platform(Permission.USER_CREATE)
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
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_platform(Permission.USER_GET)
    ),
    target_user: UserInDB = fastapi.Depends(depends_target_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> User:

    return User.model_validate_json(target_user.model_dump_json())


@router.put("/users/{user_id}", tags=["Users"])
async def api_update_user(
    user_update: UserUpdate = fastapi.Body(..., description="The user to update"),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_platform(Permission.USER_UPDATE)
    ),
    target_user: UserInDB = fastapi.Depends(depends_target_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> User:
    user_in_db = await asyncio.to_thread(
        backend_client.users.update,
        target_user.id,
        user_update,
    )
    return User.model_validate_json(user_in_db.model_dump_json())


@router.delete("/users/{user_id}", tags=["Users"])
async def api_delete_user(
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_platform(Permission.USER_DELETE)
    ),
    target_user: UserInDB = fastapi.Depends(depends_target_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    await asyncio.to_thread(
        backend_client.users.set_disabled, target_user.id, disabled=True
    )
    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)


@router.post("/users/{user_id}/enable", tags=["Users"])
async def api_enable_user(
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_platform(Permission.USER_DISABLE)
    ),
    target_user: UserInDB = fastapi.Depends(depends_target_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    await asyncio.to_thread(
        backend_client.users.set_disabled, target_user.id, disabled=False
    )

    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)


@router.get("/users/{user_id}/organizations", tags=["Users"])
async def api_list_user_organizations(
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_platform(Permission.ORG_LIST)
    ),
    target_user: UserInDB = fastapi.Depends(depends_target_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Page[Organization]:
    org_members = await asyncio.to_thread(
        backend_client.organization_members.retrieve_by_user_id,
        target_user.id,
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
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_platform(Permission.PROJECT_LIST)
    ),
    target_user: UserInDB = fastapi.Depends(depends_target_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Page[Project]:
    project_members = await asyncio.to_thread(
        backend_client.project_members.retrieve_by_user_id,
        target_user.id,
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
