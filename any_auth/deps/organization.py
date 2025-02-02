import asyncio
import logging
import typing

import fastapi

import any_auth.deps.app_state as AppState
from any_auth.backend import BackendClient
from any_auth.deps.auth import depends_active_user
from any_auth.types.organization import Organization
from any_auth.types.organization_member import OrganizationMember
from any_auth.types.role_assignment import PLATFORM_ID, RoleAssignmentListAdapter
from any_auth.types.user import UserInDB

logger = logging.getLogger(__name__)


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
    platform_role_assignments = await asyncio.to_thread(
        backend_client.role_assignments.retrieve_by_user_id,
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
