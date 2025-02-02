import asyncio
import logging
import typing

import fastapi

import any_auth.deps.app_state as AppState
import any_auth.deps.permission
from any_auth.backend import BackendClient
from any_auth.deps.auth import depends_active_user
from any_auth.deps.role_assignment import raise_if_role_assignment_denied
from any_auth.types.organization import (
    Organization,
    OrganizationCreate,
    OrganizationUpdate,
)
from any_auth.types.organization_member import (
    OrganizationMember,
    OrganizationMemberCreate,
)
from any_auth.types.pagination import Page
from any_auth.types.role import Permission, Role
from any_auth.types.role_assignment import (
    PLATFORM_ID,
    MemberRoleAssignmentCreate,
    RoleAssignment,
    RoleAssignmentListAdapter,
)
from any_auth.types.user import UserInDB

logger = logging.getLogger(__name__)

router = fastapi.APIRouter()


async def depends_organization(
    organization_id: typing.Text = fastapi.Path(
        ..., description="The ID of the organization to retrieve"
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Organization:
    might_org = await asyncio.to_thread(
        backend_client.organizations.retrieve, organization_id
    )
    if not might_org:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    return might_org


async def depends_active_organization_user(
    organization: Organization = fastapi.Depends(depends_organization),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> OrganizationMember | None:
    # Pass if user has platform roles
    platform_role_assignments = backend_client.role_assignments.retrieve_by_user_id(
        active_user.id,
        resource_id=PLATFORM_ID,
    )
    if platform_role_assignments:
        logger.info(
            f"User ({active_user.model_dump_json()}) "
            + "has platform role assignments: "
            + f"{RoleAssignmentListAdapter.dump_json(platform_role_assignments)}. "
            + "Skipping organization member check",
        )
        return None

    org_member = await asyncio.to_thread(
        backend_client.organization_members.retrieve_by_organization_user_id,
        organization.id,
        active_user.id,
    )
    if not org_member:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this organization",
        )
    if org_member.disabled:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_403_FORBIDDEN,
            detail="User is banned from this organization",
        )
    return org_member


@router.get("/organizations", tags=["Organizations"])
async def api_list_organizations(
    limit: int = fastapi.Query(default=20, ge=1, le=100),
    order: typing.Literal["asc", "desc"] = fastapi.Query(default="desc"),
    after: typing.Text = fastapi.Query(default=""),
    before: typing.Text = fastapi.Query(default=""),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    allowed_active_user_roles: typing.Tuple[
        UserInDB, typing.List[Role]
    ] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.ORG_LIST, resource_id_source="platform"
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Page[Organization]:
    page_organizations = await asyncio.to_thread(
        backend_client.organizations.list,
        limit=limit,
        order=order,
        after=after.strip() or None,
        before=before.strip() or None,
    )
    return Page[Organization].model_validate(page_organizations.model_dump())


@router.post("/organizations", tags=["Organizations"])
async def api_create_organization(
    org_create: OrganizationCreate = fastapi.Body(
        ..., description="The organization to create"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    allowed_active_user_roles: typing.Tuple[
        UserInDB, typing.List[Role]
    ] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.ORG_CREATE, resource_id_source="platform"
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Organization:
    org = await asyncio.to_thread(
        backend_client.organizations.create,
        org_create,
    )
    return Organization.model_validate(org.model_dump())


@router.get("/organizations/{organization_id}", tags=["Organizations"])
async def api_retrieve_organization(
    organization_id: typing.Text = fastapi.Path(
        ..., description="The ID of the organization to retrieve"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    organization_member: OrganizationMember = fastapi.Depends(
        depends_active_organization_user
    ),
    allowed_active_user_roles: typing.Tuple[
        UserInDB, typing.List[Role]
    ] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.ORG_GET, resource_id_source="organization"
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Organization:
    organization_id = organization_id.strip()

    if not organization_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Organization ID is required",
        )

    org = await asyncio.to_thread(
        backend_client.organizations.retrieve, organization_id
    )

    if not org:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    return Organization.model_validate(org.model_dump())


@router.post("/organizations/{organization_id}", tags=["Organizations"])
async def api_update_organization(
    organization_id: typing.Text = fastapi.Path(
        ..., description="The ID of the organization to update"
    ),
    org_update: OrganizationUpdate = fastapi.Body(
        ..., description="The organization to update"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    organization_member: OrganizationMember = fastapi.Depends(
        depends_active_organization_user
    ),
    allowed_active_user_roles: typing.Tuple[
        UserInDB, typing.List[Role]
    ] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.ORG_UPDATE, resource_id_source="organization"
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Organization:
    organization_id = organization_id.strip()

    if not organization_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Organization ID is required",
        )

    org = await asyncio.to_thread(
        backend_client.organizations.update,
        organization_id,
        org_update,
    )
    return Organization.model_validate(org.model_dump())


@router.delete("/organizations/{organization_id}", tags=["Organizations"])
async def api_delete_organization(
    organization_id: typing.Text = fastapi.Path(
        ..., description="The ID of the organization to delete"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    organization_member: OrganizationMember = fastapi.Depends(
        depends_active_organization_user
    ),
    allowed_active_user_roles: typing.Tuple[
        UserInDB, typing.List[Role]
    ] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.ORG_DELETE, resource_id_source="organization"
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    await asyncio.to_thread(
        backend_client.organizations.set_disabled, organization_id, disabled=True
    )
    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)


@router.post("/organizations/{organization_id}/enable", tags=["Organizations"])
async def api_enable_organization(
    organization_id: typing.Text = fastapi.Path(
        ..., description="The ID of the organization to enable"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    organization_member: OrganizationMember = fastapi.Depends(
        depends_active_organization_user
    ),
    allowed_active_user_roles: typing.Tuple[
        UserInDB, typing.List[Role]
    ] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.ORG_DISABLE, resource_id_source="organization"
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    await asyncio.to_thread(
        backend_client.organizations.set_disabled, organization_id, disabled=False
    )

    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)


@router.get("/organizations/{organization_id}/members", tags=["Organizations"])
async def api_list_organization_members(
    organization_id: typing.Text = fastapi.Path(
        ..., description="The ID of the organization to retrieve members for"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    organization_member: OrganizationMember = fastapi.Depends(
        depends_active_organization_user
    ),
    allowed_active_user_roles: typing.Tuple[
        UserInDB, typing.List[Role]
    ] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.ORG_MEMBER_LIST, resource_id_source="organization"
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Page[OrganizationMember]:
    org_members = await asyncio.to_thread(
        backend_client.organization_members.retrieve_by_organization_id,
        organization_id,
    )
    return Page[OrganizationMember].model_validate(
        {
            "object": "list",
            "data": org_members,
            "first_id": org_members[0].id if org_members else None,
            "last_id": org_members[-1].id if org_members else None,
            "has_more": False,
        }
    )


@router.post("/organizations/{organization_id}/members", tags=["Organizations"])
async def api_create_organization_member(
    organization_id: typing.Text = fastapi.Path(
        ..., description="The ID of the organization to create a member for"
    ),
    member_create: OrganizationMemberCreate = fastapi.Body(
        ..., description="The member to create"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    organization_member: OrganizationMember = fastapi.Depends(
        depends_active_organization_user
    ),
    allowed_active_user_roles: typing.Tuple[
        UserInDB, typing.List[Role]
    ] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.ORG_MEMBER_CREATE, resource_id_source="organization"
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> OrganizationMember:
    member = await asyncio.to_thread(
        backend_client.organization_members.create,
        member_create=member_create,
        organization_id=organization_id,
    )
    return member


@router.get(
    "/organizations/{organization_id}/members/{member_id}", tags=["Organizations"]
)
async def api_retrieve_organization_member(
    organization_id: typing.Text = fastapi.Path(
        ..., description="The ID of the organization to retrieve a member for"
    ),
    member_id: typing.Text = fastapi.Path(
        ..., description="The ID of the member to retrieve"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    organization_member: OrganizationMember = fastapi.Depends(
        depends_active_organization_user
    ),
    allowed_active_user_roles: typing.Tuple[
        UserInDB, typing.List[Role]
    ] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.ORG_MEMBER_GET, resource_id_source="organization"
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> OrganizationMember:
    member = await asyncio.to_thread(
        backend_client.organization_members.retrieve,
        member_id,
    )
    if not member:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )
    return member


@router.delete(
    "/organizations/{organization_id}/members/{member_id}", tags=["Organizations"]
)
async def api_delete_organization_member(
    organization_id: typing.Text = fastapi.Path(
        ..., description="The ID of the organization to delete a member for"
    ),
    member_id: typing.Text = fastapi.Path(
        ..., description="The ID of the member to delete"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    organization_member: OrganizationMember = fastapi.Depends(
        depends_active_organization_user
    ),
    allowed_active_user_roles: typing.Tuple[
        UserInDB, typing.List[Role]
    ] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.ORG_MEMBER_DELETE, resource_id_source="organization"
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    await asyncio.to_thread(
        backend_client.organization_members.delete,
        member_id,
    )
    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)


@router.get(
    "/organizations/{organization_id}/members/{member_id}/role-assignments",
    tags=["Organizations"],
)
async def api_retrieve_organization_member_role_assignment(
    organization_id: typing.Text = fastapi.Path(
        ..., description="The ID of the organization to retrieve a member for"
    ),
    member_id: typing.Text = fastapi.Path(
        ..., description="The ID of the member to retrieve"
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    organization_member: OrganizationMember = fastapi.Depends(
        depends_active_organization_user
    ),
    allowed_active_user_roles: typing.Tuple[
        UserInDB, typing.List[Role]
    ] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.IAM_GET_POLICY, resource_id_source="organization"
        )
    ),
) -> Page[RoleAssignment]:
    org_member = await asyncio.to_thread(
        backend_client.organization_members.retrieve,
        member_id,
    )
    if not org_member:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    if org_member.organization_id != organization_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    role_assignments = await asyncio.to_thread(
        backend_client.role_assignments.retrieve_by_user_id,
        org_member.user_id,
        resource_id=organization_id,
    )

    return Page[RoleAssignment].model_validate(
        {
            "object": "list",
            "data": role_assignments,
            "first_id": role_assignments[0].id if role_assignments else None,
            "last_id": role_assignments[-1].id if role_assignments else None,
            "has_more": False,
        }
    )


@router.post(
    "/organizations/{organization_id}/members/{member_id}/role-assignments",
    tags=["Organizations"],
)
async def api_create_organization_member_role_assignment(
    organization_id: typing.Text = fastapi.Path(
        ..., description="The ID of the organization to delete a member for"
    ),
    member_id: typing.Text = fastapi.Path(
        ..., description="The ID of the member to delete"
    ),
    member_role_assignment_create: MemberRoleAssignmentCreate = fastapi.Body(
        ..., description="The role assignment to create"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    organization_member: OrganizationMember = fastapi.Depends(
        depends_active_organization_user
    ),
    allowed_active_user_roles: typing.Tuple[
        UserInDB, typing.List[Role]
    ] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.IAM_SET_POLICY,
            resource_id_source="organization",
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> RoleAssignment:
    org_member = await asyncio.to_thread(
        backend_client.organization_members.retrieve,
        member_id,
    )
    if not org_member:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    if org_member.organization_id != organization_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    role_assignment_create = await asyncio.to_thread(
        member_role_assignment_create.to_role_assignment_create,
        backend_client=backend_client,
        user_id=org_member.user_id,
        resource_id=organization_id,
    )

    await raise_if_role_assignment_denied(
        role_assignment_create, allowed_active_user_roles, backend_client=backend_client
    )

    role_assignment = await asyncio.to_thread(
        backend_client.role_assignments.create,
        role_assignment_create,
    )

    return role_assignment


@router.delete(
    "/organizations/{organization_id}/members/{member_id}/role-assignments/{role_assignment_id}",  # noqa: E501
    tags=["Organizations"],
)
async def api_delete_organization_member_role_assignment(
    organization_id: typing.Text = fastapi.Path(
        ..., description="The ID of the organization to delete a member for"
    ),
    member_id: typing.Text = fastapi.Path(
        ..., description="The ID of the member to delete"
    ),
    role_assignment_id: typing.Text = fastapi.Path(
        ..., description="The ID of the role assignment to delete"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    organization_member: OrganizationMember = fastapi.Depends(
        depends_active_organization_user
    ),
    allowed_active_user_roles: typing.Tuple[
        UserInDB, typing.List[Role]
    ] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.IAM_SET_POLICY, resource_id_source="organization"
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    role_assignment = await asyncio.to_thread(
        backend_client.role_assignments.retrieve,
        role_assignment_id,
    )
    if not role_assignment:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Role assignment not found",
        )

    if role_assignment.resource_id != organization_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Role assignment not found",
        )

    org_member = await asyncio.to_thread(
        backend_client.organization_members.retrieve,
        member_id,
    )
    if not org_member:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    if org_member.organization_id != organization_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    if role_assignment.user_id != org_member.user_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Role assignment not found",
        )

    await asyncio.to_thread(
        backend_client.role_assignments.delete,
        role_assignment_id,
    )
    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)
