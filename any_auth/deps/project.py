import asyncio
import logging
import typing

import fastapi

import any_auth.deps.app_state as AppState
from any_auth.backend import BackendClient
from any_auth.deps.auth import depends_active_user
from any_auth.deps.organization import depends_organization
from any_auth.types.organization import Organization
from any_auth.types.project import Project
from any_auth.types.project_member import ProjectMember
from any_auth.types.role_assignment import PLATFORM_ID, RoleAssignmentListAdapter
from any_auth.types.user import UserInDB

logger = logging.getLogger(__name__)


async def depends_project(
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to retrieve"
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Project:
    might_project = await asyncio.to_thread(
        backend_client.projects.retrieve, project_id
    )
    if not might_project:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return might_project


async def depends_active_project_user(
    organization: Organization = fastapi.Depends(depends_organization),
    project: Project = fastapi.Depends(depends_project),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> ProjectMember | None:
    if organization.id != project.organization_id:
        logger.error(
            f"User ({active_user.model_dump_json()}) requested project "
            + "not in their organization: "
            + f"Organization {organization.id} does not match project {project.id}"
        )
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

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

    # Pass if user has organization roles
    organization_role_assignments = await asyncio.to_thread(
        backend_client.role_assignments.retrieve_by_user_id,
        active_user.id,
        resource_id=organization.id,
    )
    if organization_role_assignments:
        return None

    project_member = await asyncio.to_thread(
        backend_client.project_members.retrieve_by_project_user_id,
        project.id,
        active_user.id,
    )
    if not project_member:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this project",
        )
    if project_member.disabled:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_403_FORBIDDEN,
            detail="User is banned from this project",
        )
    return project_member
