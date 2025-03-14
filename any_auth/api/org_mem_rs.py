import asyncio
import logging
import typing

import fastapi

import any_auth.deps.app_state as AppState
import any_auth.deps.auth
from any_auth.backend import BackendClient
from any_auth.deps.auth import depends_active_organization, depends_active_user
from any_auth.deps.role_assignment import raise_if_role_assignment_denied
from any_auth.types.organization import Organization
from any_auth.types.organization_member import OrganizationMember
from any_auth.types.pagination import Page
from any_auth.types.role import Permission, Role
from any_auth.types.role_assignment import MemberRoleAssignmentCreate, RoleAssignment
from any_auth.types.user import UserInDB

logger = logging.getLogger(__name__)

router = fastapi.APIRouter()


async def depends_target_org_member_user(
    organization: Organization = fastapi.Depends(depends_active_organization),
    member_id: typing.Text = fastapi.Path(
        ..., description="The ID of the member to retrieve"
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> typing.Tuple[OrganizationMember, UserInDB]:
    org_member = await asyncio.to_thread(
        backend_client.organization_members.retrieve, member_id
    )

    if not org_member:
        logger.warning(f"Member ID not found: {member_id}")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    if org_member.organization_id != organization.id:
        logger.warning(
            "Member organization ID mismatch with path parameter: "
            + f"{org_member.organization_id} != {organization.id}"
        )
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    user = await asyncio.to_thread(backend_client.users.retrieve, org_member.user_id)
    if not user:
        logger.warning(f"User ID from member not found: {org_member.user_id}")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return (org_member, user)


async def depends_target_org_member_user_role_assignment(
    role_assignment_id: typing.Text = fastapi.Path(...),
    target_org_member_user: typing.Tuple[
        OrganizationMember, UserInDB
    ] = fastapi.Depends(depends_target_org_member_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> typing.Tuple[OrganizationMember, UserInDB, RoleAssignment]:
    tar_org_member, tar_user = target_org_member_user
    role_assignment = await asyncio.to_thread(
        backend_client.role_assignments.retrieve,
        role_assignment_id,
    )
    if not role_assignment:
        logger.warning(f"Role assignment ID not found: {role_assignment_id}")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Role assignment not found",
        )

    if role_assignment.resource_id != tar_org_member.organization_id:
        logger.warning(
            "Role assignment resource ID mismatch with member organization ID: "
            + f"{role_assignment.resource_id} != {tar_org_member.organization_id}"
        )
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Role assignment not found",
        )

    if role_assignment.user_id != tar_user.id:
        logger.warning(
            "Role assignment user ID mismatch with member user ID: "
            + f"{role_assignment.user_id} != {tar_user.id}"
        )
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Role assignment not found",
        )

    return (tar_org_member, tar_user, role_assignment)


@router.get(
    "/organizations/{organization_id}/members/{member_id}/rs",
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
    target_org_member_user: typing.Tuple[
        OrganizationMember, UserInDB
    ] = fastapi.Depends(depends_target_org_member_user),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    allowed_active_user_roles: typing.Tuple[
        UserInDB,
        typing.List[Role],
        typing.List[RoleAssignment],
        OrganizationMember | None,
        Organization,
    ] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_organization(
            Permission.IAM_GET_POLICY,
        )
    ),
) -> Page[RoleAssignment]:
    org_member, _ = target_org_member_user

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
    "/organizations/{organization_id}/members/{member_id}/rs",
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
    target_org_member_user: typing.Tuple[
        OrganizationMember, UserInDB
    ] = fastapi.Depends(depends_target_org_member_user),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    allowed_active_user_roles: typing.Tuple[
        UserInDB,
        typing.List[Role],
        typing.List[RoleAssignment],
        OrganizationMember | None,
        Organization,
    ] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_organization(
            Permission.IAM_SET_POLICY,
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> RoleAssignment:
    org_member, _ = target_org_member_user

    role_assignment_create = await asyncio.to_thread(
        member_role_assignment_create.to_role_assignment_create,
        backend_client=backend_client,
        user_id=org_member.user_id,
        resource_id=organization_id,
    )

    await raise_if_role_assignment_denied(
        role_assignment_create,
        allowed_active_user_roles[:2],
        backend_client=backend_client,
    )

    role_assignment = await asyncio.to_thread(
        backend_client.role_assignments.create,
        role_assignment_create,
    )

    return role_assignment


@router.delete(
    "/organizations/{organization_id}/members/{member_id}/rs/{role_assignment_id}",
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
    target_org_member_user_role_assignment: typing.Tuple[
        OrganizationMember, UserInDB, RoleAssignment
    ] = fastapi.Depends(depends_target_org_member_user_role_assignment),
    allowed_active_user_roles: typing.Tuple[
        UserInDB,
        typing.List[Role],
        typing.List[RoleAssignment],
        OrganizationMember | None,
        Organization,
    ] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_organization(
            Permission.IAM_SET_POLICY,
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    _, _, role_assignment = target_org_member_user_role_assignment

    await asyncio.to_thread(
        backend_client.role_assignments.delete,
        role_assignment.id,
    )
    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)
