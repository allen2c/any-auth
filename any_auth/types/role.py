import enum
import json
import time
import typing
import uuid

import pydantic

PLATFORM_MANAGER_ROLE_NAME: typing.Final[typing.Text] = "PlatformManager"
PLATFORM_CREATOR_ROLE_NAME: typing.Final[typing.Text] = "PlatformCreator"
ORG_OWNER_ROLE_NAME: typing.Final[typing.Text] = "OrganizationOwner"
ORG_EDITOR_ROLE_NAME: typing.Final[typing.Text] = "OrganizationEditor"
ORG_VIEWER_ROLE_NAME: typing.Final[typing.Text] = "OrganizationViewer"
PROJECT_OWNER_ROLE_NAME: typing.Final[typing.Text] = "ProjectOwner"
PROJECT_EDITOR_ROLE_NAME: typing.Final[typing.Text] = "ProjectEditor"
PROJECT_VIEWER_ROLE_NAME: typing.Final[typing.Text] = "ProjectViewer"
NA_ROLE_NAME: typing.Final[typing.Text] = "N/A"


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
    ORG_MEMBER_LIST = "organization.member.list"
    ORG_MEMBER_CREATE = "organization.member.create"
    ORG_MEMBER_GET = "organization.member.get"
    ORG_MEMBER_DELETE = "organization.member.delete"

    # --------------------
    # PROJECT Permissions
    # --------------------
    PROJECT_CREATE = "project.create"
    PROJECT_GET = "project.get"
    PROJECT_LIST = "project.list"
    PROJECT_UPDATE = "project.update"
    PROJECT_DELETE = "project.delete"
    PROJECT_DISABLE = "project.disable"
    PROJECT_MEMBER_LIST = "project.member.list"
    PROJECT_MEMBER_CREATE = "project.member.create"
    PROJECT_MEMBER_GET = "project.member.get"
    PROJECT_MEMBER_DELETE = "project.member.delete"

    # --------------------
    # API KEY Permissions
    # --------------------
    API_KEY_LIST = "api-key.list"
    API_KEY_CREATE = "api-key.create"
    API_KEY_GET = "api-key.get"
    API_KEY_UPDATE = "api-key.update"
    API_KEY_DELETE = "api-key.delete"

    # --------------------
    # IAM Permissions
    # (Policy management, roles management, etc.)
    # --------------------
    IAM_SET_POLICY = "iam.setPolicy"  # Manage IAM policies (assign roles)
    IAM_GET_POLICY = "iam.getPolicy"  # Get IAM policies
    IAM_ROLES_CREATE = "iam.roles.create"  # Create roles
    IAM_ROLES_GET = "iam.roles.get"  # Get a role
    IAM_ROLES_LIST = "iam.roles.list"  # List roles
    IAM_ROLES_UPDATE = "iam.roles.update"  # Update a role
    IAM_ROLES_DELETE = "iam.roles.delete"  # Delete a role


class Role(pydantic.BaseModel):
    id: typing.Text = pydantic.Field(default_factory=lambda: str(uuid.uuid4()))
    name: typing.Text
    permissions: typing.List[Permission] = pydantic.Field(default_factory=list)
    description: typing.Text | None = pydantic.Field(default=None)
    disabled: bool = pydantic.Field(default=False)
    parent_id: typing.Text | None = pydantic.Field(default=None)
    created_at: int = pydantic.Field(default_factory=lambda: int(time.time()))
    updated_at: int = pydantic.Field(default_factory=lambda: int(time.time()))

    _id: typing.Text | None = pydantic.PrivateAttr(default=None)

    def to_doc(self) -> typing.Dict[typing.Text, typing.Any]:
        return json.loads(self.model_dump_json())


RoleList: typing.TypeAlias = list[Role]
RoleListAdapter = pydantic.TypeAdapter(RoleList)


class RoleCreate(pydantic.BaseModel):
    name: typing.Text
    permissions: typing.List[Permission] = pydantic.Field(default_factory=list)
    description: typing.Text | None = pydantic.Field(default=None)
    disabled: bool = pydantic.Field(default=False)
    parent_id: typing.Text | None = pydantic.Field(default=None)

    def to_role(self) -> Role:
        return Role(
            name=self.name,
            permissions=self.permissions,
            description=self.description,
            parent_id=self.parent_id,
        )


class RoleUpdate(pydantic.BaseModel):
    name: typing.Text | None = pydantic.Field(default=None)
    permissions: typing.List[Permission] | None = pydantic.Field(default=None)
    description: typing.Text | None = pydantic.Field(default=None)
    # The `parent_id` field is not allowed to be updated.
    # This is to prevent cycles in the role hierarchy.


PLATFORM_MANAGER_ROLE = RoleCreate(
    name=PLATFORM_MANAGER_ROLE_NAME,
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
        Permission.ORG_MEMBER_LIST,
        Permission.ORG_MEMBER_CREATE,
        Permission.ORG_MEMBER_GET,
        Permission.ORG_MEMBER_DELETE,
        Permission.PROJECT_CREATE,
        Permission.PROJECT_GET,
        Permission.PROJECT_LIST,
        Permission.PROJECT_UPDATE,
        Permission.PROJECT_DELETE,
        Permission.PROJECT_DISABLE,
        Permission.PROJECT_MEMBER_LIST,
        Permission.PROJECT_MEMBER_CREATE,
        Permission.PROJECT_MEMBER_GET,
        Permission.PROJECT_MEMBER_DELETE,
        Permission.API_KEY_LIST,
        Permission.API_KEY_CREATE,
        Permission.API_KEY_GET,
        Permission.API_KEY_UPDATE,
        Permission.API_KEY_DELETE,
        Permission.IAM_SET_POLICY,
        Permission.IAM_GET_POLICY,
        Permission.IAM_ROLES_CREATE,
        Permission.IAM_ROLES_GET,
        Permission.IAM_ROLES_LIST,
        Permission.IAM_ROLES_UPDATE,
        Permission.IAM_ROLES_DELETE,
    ],
    description="An elevated administrative role with comprehensive control over the entire platform. Platform managers can manage users, organizations, projects, and IAM policies. This role is intended for top-level administrators who require full access and management capabilities across the authentication system.",  # noqa: E501
    parent_id=None,
)
PLATFORM_CREATOR_ROLE = RoleCreate(
    name=PLATFORM_CREATOR_ROLE_NAME,
    permissions=[
        Permission.USER_CREATE,
        Permission.USER_GET,
        Permission.USER_LIST,
        Permission.ORG_CREATE,
        Permission.ORG_GET,
        Permission.ORG_LIST,
        Permission.ORG_MEMBER_LIST,
        Permission.ORG_MEMBER_CREATE,
        Permission.ORG_MEMBER_GET,
        Permission.PROJECT_CREATE,
        Permission.PROJECT_GET,
        Permission.PROJECT_LIST,
        Permission.PROJECT_MEMBER_LIST,
        Permission.PROJECT_MEMBER_CREATE,
        Permission.PROJECT_MEMBER_GET,
        Permission.API_KEY_LIST,
        Permission.API_KEY_CREATE,
        Permission.API_KEY_GET,
        Permission.IAM_SET_POLICY,
        Permission.IAM_GET_POLICY,
        Permission.IAM_ROLES_CREATE,
        Permission.IAM_ROLES_GET,
        Permission.IAM_ROLES_LIST,
    ],
    description="A high-level administrative role that can create and manage platform-wide resources including users, organizations, projects, and IAM policies. This role is typically assigned to platform administrators responsible for initial setup and management of the authentication system.",  # noqa: E501
    parent_id="PlatformManager",
)
ORG_OWNER_ROLE = RoleCreate(
    name=ORG_OWNER_ROLE_NAME,
    permissions=[
        Permission.USER_GET,
        Permission.USER_LIST,
        Permission.USER_INVITE,
        Permission.ORG_GET,
        Permission.ORG_UPDATE,
        Permission.ORG_DELETE,
        Permission.ORG_DISABLE,
        Permission.ORG_MEMBER_LIST,
        Permission.ORG_MEMBER_CREATE,
        Permission.ORG_MEMBER_GET,
        Permission.ORG_MEMBER_DELETE,
        Permission.PROJECT_CREATE,
        Permission.PROJECT_GET,
        Permission.PROJECT_LIST,
        Permission.PROJECT_UPDATE,
        Permission.PROJECT_DELETE,
        Permission.PROJECT_DISABLE,
        Permission.PROJECT_MEMBER_LIST,
        Permission.PROJECT_MEMBER_CREATE,
        Permission.PROJECT_MEMBER_GET,
        Permission.PROJECT_MEMBER_DELETE,
        Permission.API_KEY_LIST,
        Permission.API_KEY_CREATE,
        Permission.API_KEY_GET,
        Permission.API_KEY_UPDATE,
        Permission.API_KEY_DELETE,
        Permission.IAM_SET_POLICY,
        Permission.IAM_GET_POLICY,
        Permission.IAM_ROLES_GET,
        Permission.IAM_ROLES_LIST,
    ],
    description="A role that can create and manage resources within an organization. This role is typically assigned to organization owners responsible for managing resources within an organization.",  # noqa: E501
    parent_id="PlatformManager",
)
ORG_EDITOR_ROLE = RoleCreate(
    name=ORG_EDITOR_ROLE_NAME,
    permissions=[
        Permission.ORG_GET,
        Permission.ORG_UPDATE,
        Permission.ORG_MEMBER_LIST,
        Permission.ORG_MEMBER_GET,
        Permission.PROJECT_CREATE,
        Permission.PROJECT_GET,
        Permission.PROJECT_LIST,
        Permission.PROJECT_UPDATE,
        Permission.PROJECT_DELETE,
        Permission.PROJECT_DISABLE,
        Permission.PROJECT_MEMBER_LIST,
        Permission.PROJECT_MEMBER_CREATE,
        Permission.PROJECT_MEMBER_GET,
        Permission.PROJECT_MEMBER_DELETE,
        Permission.API_KEY_LIST,
        Permission.API_KEY_GET,
        Permission.API_KEY_CREATE,
        Permission.IAM_GET_POLICY,
        Permission.IAM_ROLES_GET,
        Permission.IAM_ROLES_LIST,
    ],
    description="A role that can edit and manage resources within an organization but cannot manage organization-level settings like deletion or user invitation. This role is suitable for team members who need to manage projects and resources on a daily basis.",  # noqa: E501
    parent_id="OrganizationOwner",
)
ORG_VIEWER_ROLE = RoleCreate(
    name=ORG_VIEWER_ROLE_NAME,
    permissions=[
        Permission.ORG_GET,
        Permission.PROJECT_GET,
        Permission.ORG_MEMBER_LIST,
        Permission.ORG_MEMBER_GET,
        Permission.PROJECT_LIST,
        Permission.PROJECT_MEMBER_LIST,
        Permission.PROJECT_MEMBER_GET,
        Permission.API_KEY_LIST,
        Permission.API_KEY_GET,
        Permission.IAM_GET_POLICY,
        Permission.IAM_ROLES_GET,
        Permission.IAM_ROLES_LIST,
    ],
    description="A read-only role within an organization. Users with this role can view organization details, projects, resources, and IAM policies but cannot make any changes. This role is ideal for auditors, stakeholders, or anyone who needs to monitor the organization's resources without administrative privileges.",  # noqa: E501
    parent_id="OrganizationEditor",
)
PROJECT_OWNER_ROLE: typing.Final = RoleCreate(
    name=PROJECT_OWNER_ROLE_NAME,
    permissions=[
        Permission.PROJECT_GET,
        Permission.PROJECT_UPDATE,
        Permission.PROJECT_DELETE,
        Permission.PROJECT_DISABLE,
        Permission.PROJECT_MEMBER_LIST,
        Permission.PROJECT_MEMBER_CREATE,
        Permission.PROJECT_MEMBER_GET,
        Permission.PROJECT_MEMBER_DELETE,
        Permission.API_KEY_LIST,
        Permission.API_KEY_CREATE,
        Permission.API_KEY_GET,
        Permission.API_KEY_UPDATE,
        Permission.API_KEY_DELETE,
        Permission.IAM_SET_POLICY,
        Permission.IAM_GET_POLICY,
        Permission.IAM_ROLES_GET,
        Permission.IAM_ROLES_LIST,
    ],
    description="A role that has full control over a specific project. Project owners can manage all aspects of the project including resources, settings, and IAM policies within the project scope. This role is typically assigned to project managers or team leads responsible for the project's success.",  # noqa: E501
    parent_id="OrganizationOwner",
)
PROJECT_EDITOR_ROLE: typing.Final = RoleCreate(
    name=PROJECT_EDITOR_ROLE_NAME,
    permissions=[
        Permission.PROJECT_GET,
        Permission.PROJECT_UPDATE,
        Permission.PROJECT_MEMBER_LIST,
        Permission.PROJECT_MEMBER_GET,
        Permission.API_KEY_LIST,
        Permission.API_KEY_GET,
        Permission.API_KEY_CREATE,
        Permission.IAM_GET_POLICY,
        Permission.IAM_ROLES_GET,
        Permission.IAM_ROLES_LIST,
    ],
    description="A role that can edit and manage resources within a specific project. Project editors can create, update, and delete resources, but they do not have project-level administrative permissions like deleting the project or managing IAM policies. This role is suitable for team members who actively contribute to project resources.",  # noqa: E501
    parent_id="ProjectOwner",
)
PROJECT_VIEWER_ROLE: typing.Final = RoleCreate(
    name=PROJECT_VIEWER_ROLE_NAME,
    permissions=[
        Permission.PROJECT_GET,
        Permission.PROJECT_MEMBER_LIST,
        Permission.PROJECT_MEMBER_GET,
        Permission.API_KEY_LIST,
        Permission.API_KEY_GET,
        Permission.IAM_GET_POLICY,
        Permission.IAM_ROLES_GET,
        Permission.IAM_ROLES_LIST,
    ],
    description="A read-only role within a specific project. Users with this role can view project details, resources, and IAM policies but cannot make any changes. This role is useful for team members who need to stay informed about project progress and resources without needing to modify them.",  # noqa: E501
    parent_id="ProjectEditor",
)
NA_ROLE: typing.Final = RoleCreate(
    name=NA_ROLE_NAME,
    permissions=[],
    description="A placeholder role that does not have any permissions. This role is used when a user does not have any specific role assigned to them.",  # noqa: E501
    parent_id=None,
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
ALL_ROLES: typing.Final = PLATFORM_ROLES + TENANT_ROLES


def check_for_cycles(
    roles: typing.Iterable[Role] | typing.Iterable[RoleCreate],
    field: typing.Literal["name", "id"] = "name",
) -> bool:
    # Create a mapping of role names to their parent_id
    role_hierarchy = {getattr(role, field): role.parent_id for role in roles}

    def has_cycle(role_name, visited):
        if role_name in visited:
            return True
        parent_id = role_hierarchy.get(role_name)
        if parent_id is None:
            return False
        visited.add(role_name)
        return has_cycle(parent_id, visited)

    for role in roles:
        if has_cycle(getattr(role, field), set()):
            return True
    return False


# Check for cycles
if check_for_cycles(ALL_ROLES, field="name"):
    raise ValueError("Pre-defined roles contain a cycle in the hierarchy")
