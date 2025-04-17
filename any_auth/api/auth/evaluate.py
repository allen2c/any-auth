# any_auth/api/auth/evaluate.py
# use PDP
import asyncio
import logging
import typing

import fastapi
import pydantic

import any_auth.deps.app_state as AppState
import any_auth.deps.auth
import any_auth.utils.auth
from any_auth.backend import BackendClient
from any_auth.deps.auth import deps_active_user_or_api_key
from any_auth.types.api_key import APIKeyInDB
from any_auth.types.role import Role
from any_auth.types.role_assignment import PLATFORM_ID, RoleAssignment
from any_auth.types.user import UserInDB

logger = logging.getLogger(__name__)

router = fastapi.APIRouter()


class EvaluateRequest(pydantic.BaseModel):
    resource_id: typing.Text = pydantic.Field(
        ..., description="The ID of the resource to verify"
    )
    permissions: typing.Text = pydantic.Field(
        ..., description="Comma-separated list of permissions"
    )

    @property
    def required_permissions(self) -> typing.List[typing.Text]:
        return [perm.strip() for perm in self.permissions.split(",") if perm.strip()]


class EvaluateResponse(pydantic.BaseModel):
    success: bool
    detail: typing.Text | None = None


async def deps_roles_assignments(
    user_or_api_key: typing.Annotated[
        typing.Union[UserInDB, APIKeyInDB], fastapi.Depends(deps_active_user_or_api_key)
    ],
    evaluate_request: EvaluateRequest = fastapi.Body(...),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    roles_assignments: typing.List[RoleAssignment] = []
    for _rs in await asyncio.gather(
        asyncio.to_thread(
            backend_client.role_assignments.retrieve_by_target_id,
            target_id=user_or_api_key.id,
            resource_id=PLATFORM_ID,
        ),
        asyncio.to_thread(
            backend_client.role_assignments.retrieve_by_target_id,
            target_id=user_or_api_key.id,
            resource_id=evaluate_request.resource_id,
        ),
    ):
        roles_assignments.extend(_rs)

    return roles_assignments


async def deps_roles(
    user_or_api_key: typing.Annotated[
        typing.Union[UserInDB, APIKeyInDB], fastapi.Depends(deps_active_user_or_api_key)
    ],
    roles_assignments: typing.Annotated[
        typing.List[RoleAssignment], fastapi.Depends(deps_roles_assignments)
    ],
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    roles: typing.List[Role] = []
    if len(roles_assignments) == 0:
        logger.debug(f"No roles assignments found for target: {user_or_api_key.id}")
    else:
        role_map: typing.Dict[typing.Text, Role] = {}
        for _rs in roles_assignments:
            if _rs.role_id in role_map:
                continue

            _tar_role, _roles = await asyncio.gather(
                asyncio.to_thread(backend_client.roles.retrieve, _rs.role_id),
                asyncio.to_thread(
                    backend_client.roles.retrieve_all_child_roles, id=_rs.role_id
                ),
            )
            if _tar_role is not None:
                role_map[_tar_role.id] = _tar_role
            for _r in _roles:
                role_map[_r.id] = _r

        roles.extend(list(role_map.values()))

    return roles


@router.post("/auth/evaluate")
async def api_evaluate_bearer_token(
    user_or_api_key: typing.Annotated[
        typing.Union[UserInDB, APIKeyInDB], fastapi.Depends(deps_active_user_or_api_key)
    ],
    active_roles_assignments: typing.Annotated[
        typing.List[RoleAssignment], fastapi.Depends(deps_roles_assignments)
    ],
    active_roles: typing.Annotated[typing.List[Role], fastapi.Depends(deps_roles)],
    evaluate_request: EvaluateRequest = fastapi.Body(...),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    try:
        any_auth.utils.auth.raise_if_not_enough_permissions(
            evaluate_request.required_permissions,
            {perm for role in active_roles for perm in role.permissions},
            debug_active_user=user_or_api_key,
            debug_user_roles=active_roles,
            debug_resource_id=evaluate_request.resource_id,
        )

    except fastapi.HTTPException as e:
        if e.status_code == fastapi.status.HTTP_403_FORBIDDEN:
            return EvaluateResponse(success=False, detail=e.detail)
        else:
            raise e

    return EvaluateResponse(success=True)
