import asyncio
import logging
import typing

import fastapi

import any_auth.deps.app_state as AppState
from any_auth.backend import BackendClient
from any_auth.deps.auth import depends_active_user, deps_active_user_or_api_key
from any_auth.types.api.me import (
    MePermissionsEvaluateRequest,
    MePermissionsEvaluateResponse,
    MePermissionsResponse,
)
from any_auth.types.api_key import APIKeyInDB
from any_auth.types.organization import Organization
from any_auth.types.pagination import Page
from any_auth.types.project import Project
from any_auth.types.role import Role
from any_auth.types.role_assignment import RoleAssignment
from any_auth.types.user import User, UserInDB

logger = logging.getLogger(__name__)

router = fastapi.APIRouter(tags=["Me"])


@router.get("/me", response_model=User)
async def api_me(active_user: UserInDB = fastapi.Depends(depends_active_user)) -> User:
    """Get current authenticated user information."""
    return User.model_validate(active_user.model_dump())


@router.get("/me/organizations", response_model=Page[Organization])
async def api_me_organizations(
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Page[Organization]:
    """Get organizations that the current user belongs to."""
    # Get organization memberships
    organization_members = await asyncio.to_thread(
        backend_client.organization_members.retrieve_by_user_id, active_user.id
    )

    # Extract organization IDs
    organization_ids = [
        member.organization_id
        for member in organization_members
        if member.organization_id
    ]

    if not organization_ids:
        return Page(object="list", data=[], first_id=None, last_id=None, has_more=False)

    # Get organization details
    organizations = await asyncio.to_thread(
        backend_client.organizations.retrieve_by_ids, organization_ids
    )

    return Page(
        object="list",
        data=organizations,
        first_id=organizations[0].id if organizations else None,
        last_id=organizations[-1].id if organizations else None,
        has_more=False,
    )


@router.get("/me/projects", response_model=Page[Project])
async def api_me_projects(
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Page[Project]:
    """Get projects that the current user has access to."""
    # Get project memberships
    project_members = await asyncio.to_thread(
        backend_client.project_members.retrieve_by_user_id, active_user.id
    )

    # Extract project IDs
    project_ids = [member.project_id for member in project_members if member.project_id]

    if not project_ids:
        logger.debug(f"User '{active_user.id}' has no projects")
        return Page(object="list", data=[], first_id=None, last_id=None, has_more=False)

    logger.debug(f"User '{active_user.id}' has {len(project_ids)} projects")

    # Get project details
    projects = await asyncio.to_thread(
        backend_client.projects.retrieve_by_ids, project_ids
    )

    return Page(
        object="list",
        data=projects,
        first_id=projects[0].id if projects else None,
        last_id=projects[-1].id if projects else None,
        has_more=False,
    )


@router.get("/me/permissions", response_model=MePermissionsResponse)
async def api_me_permissions(
    project_id: typing.Text | None = fastapi.Query(
        default=None, description="The ID of the project to check permissions for"
    ),
    projectId: typing.Text | None = fastapi.Query(default=None),
    organization_id: typing.Text | None = fastapi.Query(
        default=None, description="The ID of the organization to check permissions for"
    ),
    organizationId: typing.Text | None = fastapi.Query(default=None),
    resource_id: typing.Text | None = fastapi.Query(
        default=None, description="The ID of the resource to check permissions for"
    ),
    resourceId: typing.Text | None = fastapi.Query(default=None),
    active_user_or_api_key: typing.Union[UserInDB, APIKeyInDB] = fastapi.Depends(
        deps_active_user_or_api_key
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    target_resource_id = (
        project_id
        or projectId
        or organization_id
        or organizationId
        or resource_id
        or resourceId
    )
    if not target_resource_id:
        raise fastapi.HTTPException(
            status_code=400,
            detail="At least one of project_id, organization_id, or resource_id must be provided",  # noqa: E501
        )

    return await MePermissionsHandler.get_roles_of_user_or_api_key_in_resource(
        resource_id=target_resource_id,
        resource_type=(
            "project"
            if (project_id or projectId)
            else "organization" if (organization_id or organizationId) else None
        ),
        user_or_api_key=active_user_or_api_key,
        backend_client=backend_client,
    )


@router.post("/me/permissions/evaluate", response_model=MePermissionsEvaluateResponse)
async def api_me_permissions_evaluate(
    project_id: typing.Text | None = fastapi.Query(
        default=None, description="The ID of the project to check permissions for"
    ),
    projectId: typing.Text | None = fastapi.Query(default=None),
    organization_id: typing.Text | None = fastapi.Query(
        default=None, description="The ID of the organization to check permissions for"
    ),
    organizationId: typing.Text | None = fastapi.Query(default=None),
    resource_id: typing.Text | None = fastapi.Query(
        default=None, description="The ID of the resource to check permissions for"
    ),
    resourceId: typing.Text | None = fastapi.Query(default=None),
    evaluate_request: MePermissionsEvaluateRequest = fastapi.Body(...),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
    active_user_or_api_key: typing.Union[UserInDB, APIKeyInDB] = fastapi.Depends(
        deps_active_user_or_api_key
    ),
):
    target_resource_id = (
        project_id
        or projectId
        or organization_id
        or organizationId
        or resource_id
        or resourceId
    )
    if not target_resource_id:
        raise fastapi.HTTPException(
            status_code=400,
            detail="At least one of project_id, organization_id, or resource_id must be provided",  # noqa: E501
        )

    me_permissions_response = (
        await MePermissionsHandler.get_roles_of_user_or_api_key_in_resource(
            resource_id=target_resource_id,
            resource_type=(
                "project"
                if (project_id or projectId)
                else "organization" if (organization_id or organizationId) else None
            ),
            user_or_api_key=active_user_or_api_key,
            backend_client=backend_client,
        )
    )

    granted = set(me_permissions_response.permissions) & set(
        evaluate_request.permissions_to_check
    )
    missing = set(evaluate_request.permissions_to_check) - set(
        me_permissions_response.permissions
    )

    return MePermissionsEvaluateResponse(
        allowed=len(missing) == 0,
        user_id=me_permissions_response.user_id,
        api_key_id=me_permissions_response.api_key_id,
        resource_id=me_permissions_response.resource_id,
        granted_permissions=list(granted),
        missing_permissions=list(missing),
        details=me_permissions_response.details,
    )


class MePermissionsHandler:
    @staticmethod
    async def get_roles_of_user_or_api_key_in_resource(
        *,
        resource_id: typing.Text,
        resource_type: typing.Literal["project", "organization", None],
        user_or_api_key: typing.Union[UserInDB, APIKeyInDB],
        backend_client: BackendClient,
    ) -> MePermissionsResponse:

        if isinstance(user_or_api_key, APIKeyInDB):
            return await MePermissionsHandler.get_roles_of_api_key_in_resource(
                resource_id=resource_id,
                api_key=user_or_api_key,
                backend_client=backend_client,
            )

        elif isinstance(user_or_api_key, UserInDB):
            return await MePermissionsHandler.get_roles_of_user_in_resource(
                resource_id=resource_id,
                resource_type=resource_type,
                user=user_or_api_key,
                backend_client=backend_client,
            )

        else:
            raise fastapi.HTTPException(
                status_code=400,
                detail="Invalid active user or API key",
            )

    @staticmethod
    async def get_roles_of_user_in_resource(
        *,
        resource_id: typing.Text,
        resource_type: typing.Literal["project", "organization", None],
        user: UserInDB,
        backend_client: BackendClient,
    ) -> MePermissionsResponse:
        if resource_type == "project":
            return await MePermissionsHandler.get_roles_of_user_in_project(
                project_id=resource_id,
                active_user=user,
                backend_client=backend_client,
            )
        elif resource_type == "organization":
            return await MePermissionsHandler.get_roles_of_user_in_organization(
                organization_id=resource_id,
                active_user=user,
                backend_client=backend_client,
            )

        else:
            might_project_id = await asyncio.to_thread(
                backend_client.projects.retrieve, resource_id
            )
            if might_project_id:
                return await MePermissionsHandler.get_roles_of_user_in_project(
                    project_id=resource_id,
                    active_user=user,
                    backend_client=backend_client,
                )

            might_organization_id = await asyncio.to_thread(
                backend_client.organizations.retrieve, resource_id
            )
            if might_organization_id:
                return await MePermissionsHandler.get_roles_of_user_in_organization(
                    organization_id=resource_id,
                    active_user=user,
                    backend_client=backend_client,
                )

            raise fastapi.HTTPException(
                status_code=404,
                detail=f"Resource '{resource_id}' not found",
            )

    @staticmethod
    async def get_roles_of_user_in_project(
        *,
        project_id: typing.Text,
        active_user: UserInDB,
        backend_client: BackendClient,
        with_child_roles: bool = True,
    ) -> MePermissionsResponse:
        project_member = await asyncio.to_thread(
            backend_client.project_members.retrieve_by_project_user_id,
            project_id=project_id,
            user_id=active_user.id,
        )
        if not project_member:
            return MePermissionsResponse(
                resource_id=project_id,
                user_id=active_user.id,
                api_key_id=None,
                roles=[],
                permissions=[],
                details={"error": "Not a project member"},
            )

        _role_assignments = await asyncio.to_thread(
            backend_client.role_assignments.retrieve_by_member_id,
            member_id=project_member.id,
            type="project",
            resource_id=project_id,
        )
        if len(_role_assignments) == 0:
            return MePermissionsResponse(
                resource_id=project_id,
                user_id=active_user.id,
                api_key_id=None,
                roles=[],
                permissions=[],
                details={"error": "No roles assigned to project member"},
            )

        _roles = await MePermissionsHandler.roles_from_role_assignments(
            role_assignments=_role_assignments, backend_client=backend_client
        )

        if with_child_roles and len(_roles) > 0:
            _roles = await MePermissionsHandler.roles_from_parent_roles(
                roles=_roles,
                backend_client=backend_client,
            )

        return MePermissionsResponse(
            resource_id=project_id,
            user_id=active_user.id,
            api_key_id=None,
            roles=_roles,
            permissions=[p for r in _roles for p in r.permissions],
        )

    @staticmethod
    async def get_roles_of_user_in_organization(
        *,
        organization_id: typing.Text,
        active_user: UserInDB,
        backend_client: BackendClient,
        with_child_roles: bool = True,
    ) -> MePermissionsResponse:
        org_member = await asyncio.to_thread(
            backend_client.organization_members.retrieve_by_organization_user_id,
            organization_id=organization_id,
            user_id=active_user.id,
        )
        if not org_member:
            return MePermissionsResponse(
                resource_id=organization_id,
                user_id=active_user.id,
                api_key_id=None,
                roles=[],
                permissions=[],
                details={"error": "Not an organization member"},
            )

        _role_assignments = await asyncio.to_thread(
            backend_client.role_assignments.retrieve_by_member_id,
            member_id=org_member.id,
            type="organization",
            resource_id=organization_id,
        )

        if len(_role_assignments) == 0:
            return MePermissionsResponse(
                resource_id=organization_id,
                user_id=active_user.id,
                api_key_id=None,
                roles=[],
                permissions=[],
                details={"error": "No roles assigned to organization member"},
            )

        _roles = await MePermissionsHandler.roles_from_role_assignments(
            role_assignments=_role_assignments, backend_client=backend_client
        )

        if with_child_roles and len(_roles) > 0:
            _roles = await MePermissionsHandler.roles_from_parent_roles(
                roles=_roles, backend_client=backend_client
            )

        return MePermissionsResponse(
            resource_id=organization_id,
            user_id=active_user.id,
            api_key_id=None,
            roles=_roles,
            permissions=[p for r in _roles for p in r.permissions],
        )

    @staticmethod
    async def get_roles_of_api_key_in_resource(
        *,
        resource_id: typing.Text,
        api_key: APIKeyInDB,
        backend_client: BackendClient,
        with_child_roles: bool = True,
    ) -> MePermissionsResponse:
        if resource_id and api_key.resource_id != resource_id:
            raise fastapi.HTTPException(
                status_code=401,
                detail="Insufficient permissions",
            )

        _role_assignments = await asyncio.to_thread(
            backend_client.role_assignments.retrieve_by_target_id,
            target_id=api_key.id,
            resource_id=resource_id,
        )

        _roles = await MePermissionsHandler.roles_from_role_assignments(
            role_assignments=_role_assignments, backend_client=backend_client
        )

        if with_child_roles and len(_roles) > 0:
            _roles = await MePermissionsHandler.roles_from_parent_roles(
                roles=_roles, backend_client=backend_client
            )

        return MePermissionsResponse(
            resource_id=resource_id,
            user_id=None,
            api_key_id=api_key.id,
            roles=_roles,
            permissions=[p for r in _roles for p in r.permissions],
        )

    @staticmethod
    async def roles_from_role_assignments(
        *,
        role_assignments: typing.List[RoleAssignment],
        backend_client: BackendClient,
    ) -> typing.List[Role]:
        _roles = await asyncio.to_thread(
            backend_client.roles.retrieve_by_ids,
            [assignment.role_id for assignment in role_assignments],
        )
        return _roles

    @staticmethod
    async def roles_from_parent_roles(
        *, roles: typing.List[Role], backend_client: BackendClient
    ) -> typing.List[Role]:
        role_map: typing.Dict[typing.Text, Role] = {_r.id: _r for _r in roles}
        for _r in roles:
            _roles = await asyncio.to_thread(
                backend_client.roles.retrieve_all_child_roles,
                id=_r.id,
            )
            for _r in _roles:
                role_map[_r.id] = _r

        return list(role_map.values())
