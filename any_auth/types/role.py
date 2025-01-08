import enum
import json
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
    # RESOURCE Permissions
    # --------------------
    RESOURCE_CREATE = "resource.create"
    RESOURCE_GET = "resource.get"
    RESOURCE_LIST = "resource.list"
    RESOURCE_UPDATE = "resource.update"
    RESOURCE_DELETE = "resource.delete"

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

    _id: typing.Text | None = pydantic.PrivateAttr(default=None)

    def to_doc(self) -> typing.Dict[typing.Text, typing.Any]:
        return json.loads(self.model_dump_json())


class RoleCreate(Role):
    name: typing.Text
    permissions: typing.List[Permission] = pydantic.Field(default_factory=list)
    description: typing.Text | None = pydantic.Field(default=None)

    def to_role(self) -> Role:
        return Role(
            name=self.name,
            permissions=self.permissions,
            description=self.description,
        )


PLATFORM_CREATOR_ROLE: typing.Final = Role(
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
ORG_OWNER_ROLE: typing.Final = Role(
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
        Permission.RESOURCE_CREATE,
        Permission.RESOURCE_GET,
        Permission.RESOURCE_LIST,
        Permission.RESOURCE_UPDATE,
        Permission.RESOURCE_DELETE,
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


PREDEFINED_ROLES: typing.Final = (
    PLATFORM_CREATOR_ROLE,
    ORG_OWNER_ROLE,
)
