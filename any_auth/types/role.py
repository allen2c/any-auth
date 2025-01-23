import enum
import json
import time
import typing
import uuid

import pydantic


class Permission(enum.StrEnum):
    # --------------------
    # USER Permissions
    # --------------------
    USER_CREATE = "user.create"  # Create new user accounts
    USER_GET = "user.get"  # Get details about a specific user
    USER_LIST = "user.list"  # List all users
    USER_UPDATE = "user.update"  # Update user data (profile, settings)
    USER_DELETE = "user.delete"  # Permanently delete a user
    USER_DISABLE = "user.disable"  # Disable a user without deleting
    USER_INVITE = "user.invite"  # Send an invite or trigger an onboarding flow

    # --------------------
    # ORGANIZATION Permissions
    # --------------------
    ORG_CREATE = "organization.create"
    ORG_GET = "organization.get"
    ORG_LIST = "organization.list"
    ORG_UPDATE = "organization.update"
    ORG_DELETE = "organization.delete"
    ORG_DISABLE = "organization.disable"

    # --------------------
    # PROJECT Permissions
    # --------------------
    PROJECT_CREATE = "project.create"
    PROJECT_GET = "project.get"
    PROJECT_LIST = "project.list"
    PROJECT_UPDATE = "project.update"
    PROJECT_DELETE = "project.delete"
    PROJECT_DISABLE = "project.disable"

    # --------------------
    # IAM Permissions
    # (Policy management, roles management, etc.)
    # --------------------
    IAM_SET_POLICY = "iam.setPolicy"  # Manage IAM policies (assign roles)
    IAM_GET_POLICY = "iam.getPolicy"  # Get IAM policies
    IAM_ROLES_CREATE = "iam.roles.create"  # Create a custom role
    IAM_ROLES_GET = "iam.roles.get"  # Get a custom role
    IAM_ROLES_LIST = "iam.roles.list"  # List custom roles
    IAM_ROLES_UPDATE = "iam.roles.update"  # Update a custom role
    IAM_ROLES_DELETE = "iam.roles.delete"  # Delete a custom role


class Role(pydantic.BaseModel):
    id: typing.Text = pydantic.Field(default_factory=lambda: str(uuid.uuid4()))
    name: typing.Text
    permissions: typing.List[Permission] = pydantic.Field(default_factory=list)
    description: typing.Text | None = pydantic.Field(default=None)
    disabled: bool = pydantic.Field(default=False)
    created_at: int = pydantic.Field(default_factory=lambda: int(time.time()))
    updated_at: int = pydantic.Field(default_factory=lambda: int(time.time()))

    _id: typing.Text | None = pydantic.PrivateAttr(default=None)

    def to_doc(self) -> typing.Dict[typing.Text, typing.Any]:
        return json.loads(self.model_dump_json())


class RoleCreate(pydantic.BaseModel):
    name: typing.Text
    permissions: typing.List[Permission] = pydantic.Field(default_factory=list)
    description: typing.Text | None = pydantic.Field(default=None)
    disabled: bool = pydantic.Field(default=False)

    def to_role(self) -> Role:
        return Role(
            name=self.name,
            permissions=self.permissions,
            description=self.description,
        )


class RoleUpdate(pydantic.BaseModel):
    name: typing.Text | None = pydantic.Field(default=None)
    permissions: typing.List[Permission] | None = pydantic.Field(default=None)
    description: typing.Text | None = pydantic.Field(default=None)


PLATFORM_MANAGER_ROLE: typing.Final = RoleCreate(
    name="PlatformManager",
    permissions=[
        Permission.USER_CREATE,
        Permission.USER_GET,
        Permission.USER_LIST,
        Permission.USER_UPDATE,
        Permission.USER_DELETE,
        Permission.USER_DISABLE,
        Permission.ORG_CREATE,
        Permission.ORG_GET,
        Permission.ORG_LIST,
        Permission.ORG_UPDATE,
        Permission.ORG_DELETE,
        Permission.ORG_DISABLE,
        Permission.PROJECT_CREATE,
        Permission.PROJECT_GET,
        Permission.PROJECT_LIST,
        Permission.PROJECT_UPDATE,
        Permission.PROJECT_DELETE,
        Permission.PROJECT_DISABLE,
        Permission.IAM_SET_POLICY,
        Permission.IAM_GET_POLICY,
        Permission.IAM_ROLES_CREATE,
        Permission.IAM_ROLES_GET,
        Permission.IAM_ROLES_LIST,
        Permission.IAM_ROLES_UPDATE,
        Permission.IAM_ROLES_DELETE,
    ],
    description="An elevated administrative role with comprehensive control over the entire platform. Platform managers can manage users, organizations, projects, and IAM policies. This role is intended for top-level administrators who require full access and management capabilities across the authentication system.",  # noqa: E501
)
PLATFORM_CREATOR_ROLE: typing.Final = RoleCreate(
    name="PlatformCreator",
    permissions=[
        Permission.USER_CREATE,
        Permission.USER_GET,
        Permission.USER_LIST,
        Permission.ORG_CREATE,
        Permission.ORG_GET,
        Permission.ORG_LIST,
        Permission.PROJECT_CREATE,
        Permission.PROJECT_GET,
        Permission.PROJECT_LIST,
        Permission.IAM_SET_POLICY,
        Permission.IAM_GET_POLICY,
        Permission.IAM_ROLES_CREATE,
        Permission.IAM_ROLES_GET,
        Permission.IAM_ROLES_LIST,
    ],
    description="A high-level administrative role that can create and manage platform-wide resources including users, organizations, projects, and IAM policies. This role is typically assigned to platform administrators responsible for initial setup and management of the authentication system.",  # noqa: E501
)
ORG_OWNER_ROLE: typing.Final = RoleCreate(
    name="OrganizationOwner",
    permissions=[
        Permission.USER_GET,
        Permission.USER_LIST,
        Permission.USER_INVITE,
        Permission.ORG_GET,
        Permission.ORG_UPDATE,
        Permission.ORG_DELETE,
        Permission.ORG_DISABLE,
        Permission.PROJECT_CREATE,
        Permission.PROJECT_GET,
        Permission.PROJECT_LIST,
        Permission.PROJECT_UPDATE,
        Permission.PROJECT_DELETE,
        Permission.PROJECT_DISABLE,
        Permission.IAM_SET_POLICY,
        Permission.IAM_GET_POLICY,
        Permission.IAM_ROLES_CREATE,
        Permission.IAM_ROLES_GET,
        Permission.IAM_ROLES_LIST,
        Permission.IAM_ROLES_UPDATE,
        Permission.IAM_ROLES_DELETE,
    ],
    description="A role that can create and manage resources within an organization. This role is typically assigned to organization owners responsible for managing resources within an organization.",  # noqa: E501
)
ORG_EDITOR_ROLE: typing.Final = RoleCreate(
    name="OrganizationEditor",
    permissions=[
        Permission.ORG_GET,
        Permission.ORG_UPDATE,
        Permission.PROJECT_CREATE,
        Permission.PROJECT_GET,
        Permission.PROJECT_LIST,
        Permission.PROJECT_UPDATE,
        Permission.PROJECT_DELETE,
        Permission.PROJECT_DISABLE,
        Permission.IAM_GET_POLICY,
        Permission.IAM_ROLES_GET,
        Permission.IAM_ROLES_LIST,
    ],
    description="A role that can edit and manage resources within an organization but cannot manage organization-level settings like deletion or user invitation. This role is suitable for team members who need to manage projects and resources on a daily basis.",  # noqa: E501
)
ORG_VIEWER_ROLE: typing.Final = RoleCreate(
    name="OrganizationViewer",
    permissions=[
        Permission.ORG_GET,
        Permission.PROJECT_GET,
        Permission.PROJECT_LIST,
        Permission.IAM_GET_POLICY,
        Permission.IAM_ROLES_GET,
        Permission.IAM_ROLES_LIST,
    ],
    description="A read-only role within an organization. Users with this role can view organization details, projects, resources, and IAM policies but cannot make any changes. This role is ideal for auditors, stakeholders, or anyone who needs to monitor the organization's resources without administrative privileges.",  # noqa: E501
)
PROJECT_OWNER_ROLE: typing.Final = RoleCreate(
    name="ProjectOwner",
    permissions=[
        Permission.PROJECT_GET,
        Permission.PROJECT_UPDATE,
        Permission.PROJECT_DELETE,
        Permission.PROJECT_DISABLE,
        Permission.IAM_SET_POLICY,
        Permission.IAM_GET_POLICY,
        Permission.IAM_ROLES_CREATE,
        Permission.IAM_ROLES_GET,
        Permission.IAM_ROLES_LIST,
        Permission.IAM_ROLES_UPDATE,
        Permission.IAM_ROLES_DELETE,
    ],
    description="A role that has full control over a specific project. Project owners can manage all aspects of the project including resources, settings, and IAM policies within the project scope. This role is typically assigned to project managers or team leads responsible for the project's success.",  # noqa: E501
)
PROJECT_EDITOR_ROLE: typing.Final = RoleCreate(
    name="ProjectEditor",
    permissions=[
        Permission.PROJECT_GET,
        Permission.PROJECT_UPDATE,
        Permission.IAM_GET_POLICY,
        Permission.IAM_ROLES_GET,
        Permission.IAM_ROLES_LIST,
    ],
    description="A role that can edit and manage resources within a specific project. Project editors can create, update, and delete resources, but they do not have project-level administrative permissions like deleting the project or managing IAM policies. This role is suitable for team members who actively contribute to project resources.",  # noqa: E501
)
PROJECT_VIEWER_ROLE: typing.Final = RoleCreate(
    name="ProjectViewer",
    permissions=[
        Permission.PROJECT_GET,
        Permission.IAM_GET_POLICY,
        Permission.IAM_ROLES_GET,
        Permission.IAM_ROLES_LIST,
    ],
    description="A read-only role within a specific project. Users with this role can view project details, resources, and IAM policies but cannot make any changes. This role is useful for team members who need to stay informed about project progress and resources without needing to modify them.",  # noqa: E501
)


PLATFORM_ROLES: typing.Final = (
    PLATFORM_MANAGER_ROLE,
    PLATFORM_CREATOR_ROLE,
)
TENANT_ROLES: typing.Final = (
    ORG_OWNER_ROLE,
    ORG_EDITOR_ROLE,
    ORG_VIEWER_ROLE,
    PROJECT_OWNER_ROLE,
    PROJECT_EDITOR_ROLE,
    PROJECT_VIEWER_ROLE,
)
