# any_auth/api/v1/organizations/members/route.py
# use RBAC
import asyncio
import logging
import typing

import fastapi

import any_auth.deps.app_state as AppState
import any_auth.deps.auth
from any_auth.backend import BackendClient
from any_auth.deps.auth import depends_active_user
from any_auth.types.organization import Organization
from any_auth.types.organization_member import (
    OrganizationMember,
    OrganizationMemberCreate,
)
from any_auth.types.pagination import Page
from any_auth.types.role import Permission, Role
from any_auth.types.role_assignment import RoleAssignment
from any_auth.types.user import UserInDB

from .role_assignments.route import router as rs_router

logger = logging.getLogger(__name__)

router = fastapi.APIRouter()


@router.get("/organizations/{organization_id}/members", tags=["Organizations"])
async def api_list_organization_members(
    organization_id: typing.Text = fastapi.Path(
        ..., description="The ID of the organization to retrieve members for"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    allowed_active_user_roles: typing.Tuple[
        UserInDB,
        typing.List[Role],
        typing.List[RoleAssignment],
        OrganizationMember | None,
        Organization,
    ] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_organization(
            Permission.ORG_MEMBER_LIST,
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
    allowed_active_user_roles: typing.Tuple[
        UserInDB,
        typing.List[Role],
        typing.List[RoleAssignment],
        OrganizationMember | None,
        Organization,
    ] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_organization(
            Permission.ORG_MEMBER_CREATE,
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
    allowed_active_user_roles: typing.Tuple[
        UserInDB,
        typing.List[Role],
        typing.List[RoleAssignment],
        OrganizationMember | None,
        Organization,
    ] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_organization(
            Permission.ORG_MEMBER_GET,
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
    if member.organization_id != organization_id:
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
    allowed_active_user_roles: typing.Tuple[
        UserInDB,
        typing.List[Role],
        typing.List[RoleAssignment],
        OrganizationMember | None,
        Organization,
    ] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_organization(
            Permission.ORG_MEMBER_DELETE,
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    target_org_member = await asyncio.to_thread(
        backend_client.organization_members.retrieve,
        member_id,
    )
    if not target_org_member:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )
    if target_org_member.organization_id != organization_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    await asyncio.to_thread(
        backend_client.organization_members.delete,
        member_id,
    )

    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)


router.include_router(rs_router)
