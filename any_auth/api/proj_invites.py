import asyncio
import logging
import textwrap
import time
import typing

import fastapi
import fastapi_mail.fastmail
import fastapi_mail.schemas
import jinja2

import any_auth.deps.app_state as AppState
import any_auth.deps.auth
from any_auth.backend import BackendClient
from any_auth.config import Settings
from any_auth.deps.auth import depends_active_user
from any_auth.types.role_assignment import RoleAssignmentCreate
from any_auth.types.invite import Invite, InviteCreate, InviteInDB
from any_auth.types.pagination import Page
from any_auth.types.project import Project
from any_auth.types.project_member import ProjectMember, ProjectMemberCreate
from any_auth.types.role import Permission, Role, PROJECT_VIEWER_ROLE_NAME
from any_auth.types.user import UserInDB

logger = logging.getLogger(__name__)

router = fastapi.APIRouter()


async def deps_project(
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to invite members to"
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Project:
    project = await asyncio.to_thread(backend_client.projects.retrieve, project_id)
    if not project:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


async def deps_target_user(
    invite_create: InviteCreate = fastapi.Body(..., description="The invite to create"),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> UserInDB:
    target_user = await asyncio.to_thread(
        backend_client.users.retrieve_by_email, invite_create.email
    )
    if not target_user:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return target_user


@router.post("/projects/{project_id}/invites", tags=["Projects"])
async def api_create_project_invite(
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to invite members to"
    ),
    use_smtp: bool = fastapi.Query(default=True, description="Whether to use SMTP"),
    invite_create: InviteCreate = fastapi.Body(..., description="The invite to create"),
    project: Project = fastapi.Depends(deps_project),
    target_user: UserInDB = fastapi.Depends(deps_target_user),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    active_user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_project(
            Permission.PROJECT_MEMBER_CREATE,
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
    settings: Settings = fastapi.Depends(AppState.depends_settings),
    smtp_mailer: fastapi_mail.fastmail.FastMail = fastapi.Depends(
        AppState.depends_smtp_mailer
    ),
) -> InviteInDB:
    """Create a project invite and send an invitation email."""

    # Check if invite already exists
    existing_invite = await asyncio.to_thread(
        backend_client.invites.retrieve_by_email_and_resource_id,
        invite_create.email,
        project_id,
    )
    if existing_invite is not None:
        if existing_invite.expires_at > time.time():
            logger.warning(
                f"Invite already exists for {invite_create.email} "
                + f"in project {project_id}"
            )
            return InviteInDB.model_validate_json(existing_invite.model_dump_json())
        else:
            logger.warning(
                f"Invite already exists for {invite_create.email} "
                + f"in project {project_id} but has expired"
            )
            await asyncio.to_thread(backend_client.invites.delete, existing_invite.id)

    # Create the project invite
    project_invite = await asyncio.to_thread(
        backend_client.invites.create,
        invite_create,
        resource_id=project_id,
        invited_by=active_user.id,
    )

    # Build the invite URL
    # In a real app, this would be configured from settings
    base_url = "http://localhost:3000"
    invite_path = f"/projects/{project_id}/accept-invite"
    invite_url = f"{base_url}{invite_path}?token={project_invite.temporary_token}"

    # Send email
    if use_smtp and settings.is_smtp_configured():
        # Create a Jinja2 template for the email
        template = jinja2.Template(
            textwrap.dedent(
                """
                <html>
                <body>
                <h1>Project Invitation</h1>
                <p>You have been invited to join the project <strong>{{ project_name }}</strong>.</p>
                <p>Click the link below to accept the invitation:</p>
                <p><a href="{{ invite_url }}">Accept Invitation</a></p>
                    <p>This invitation will expire in 15 minutes.</p>
                </body>
                </html>
                """  # noqa: E501
            ).strip()
        )

        # Render the template with context variables
        html_content = template.render(project_name=project.name, invite_url=invite_url)

        email_schema = fastapi_mail.schemas.MessageSchema(
            subject=f"Invitation to join project {project.name}",
            recipients=[project_invite.email],
            body=html_content,
            subtype=fastapi_mail.schemas.MessageType.html,
        )

        try:
            await smtp_mailer.send_message(email_schema)
            logger.info(f"Sent project invite email to {project_invite.email}")

        except Exception as e:
            logger.error(f"Failed to send project invite email: {e}")
            # Don't fail the API call if email sending fails

    else:
        logger.warning("SMTP not configured, skipping invite email")

    return project_invite


@router.get("/projects/{project_id}/invites", tags=["Projects"])
async def api_list_project_invites(
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to retrieve invites for"
    ),
    limit: typing.Optional[int] = fastapi.Query(default=20),
    after: typing.Optional[typing.Text] = fastapi.Query(default=None),
    before: typing.Optional[typing.Text] = fastapi.Query(default=None),
    order: typing.Literal["asc", "desc", 1, -1] = fastapi.Query(default="desc"),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    active_user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_project(
            Permission.PROJECT_MEMBER_LIST,
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Page[Invite]:
    """List all invites for a project."""

    page_invites = await asyncio.to_thread(
        backend_client.invites.list,
        resource_id=project_id,
        limit=limit,
        after=after,
        before=before,
        order=order,
    )

    return Page[Invite].model_validate_json(page_invites.model_dump_json())


@router.post("/projects/{project_id}/accept-invite", tags=["Projects"])
async def api_accept_project_invite(
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to accept an invite for"
    ),
    project: Project = fastapi.Depends(deps_project),
    token: typing.Text = fastapi.Query(
        ..., description="The invite token received in the email"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
    settings: Settings = fastapi.Depends(AppState.depends_settings),
) -> ProjectMember:
    """Accept a project invite by validating the token and adding the user as a project member."""  # noqa: E501

    # Retrieve the invite
    invite = await asyncio.to_thread(
        backend_client.invites.retrieve_by_temporary_token,
        token,
        email=active_user.email,  # User should login with the email they were invited with  # noqa: E501
        resource_id=project_id,
    )

    # Raise an error if the invite is not found
    if not invite:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Invite not found",
        )

    # Raise an error if the invite has expired
    if invite.expires_at < time.time():
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Invite expired",
        )

    # Create the project member
    try:
        member_create = ProjectMemberCreate(
            user_id=active_user.id,
            metadata={"invited_by": invite.invited_by},
        )
        project_member = await asyncio.to_thread(
            backend_client.project_members.create,
            member_create,
            project_id=project_id,
        )

    except Exception as e:
        logger.error(f"Failed to create project member: {e}")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project member",
        ) from e

    # Get the project viewer role
    role_proj_viewer = await asyncio.to_thread(
        backend_client.roles.retrieve_by_name, PROJECT_VIEWER_ROLE_NAME
    )
    if role_proj_viewer is None:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Project viewer role not found, the service is misconfigured",
        )

    # Assign the project viewer role to the user
    try:
        await asyncio.to_thread(
            backend_client.role_assignments.create,
            role_assignment_create=RoleAssignmentCreate(
                target_id=active_user.id,
                role_id=role_proj_viewer.id,
                resource_id=project_id,
            ),
        )
    except Exception as e:
        logger.error(f"Failed to assign project viewer role: {e}")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign project viewer role",
        ) from e

    # Delete the invite since it's been used
    await asyncio.to_thread(backend_client.invites.delete, invite.id)

    return project_member
