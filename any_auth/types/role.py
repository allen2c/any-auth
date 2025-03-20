import enum
import json
import pathlib
import time
import typing
import uuid

import pydantic
import yaml

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
    name: typing.Literal[
        "PlatformManager",
        "PlatformCreator",
        "OrganizationOwner",
        "OrganizationEditor",
        "OrganizationViewer",
        "ProjectOwner",
        "ProjectEditor",
        "ProjectViewer",
        "N/A",
    ]
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


_roles_definitions_raw = yaml.safe_load(
    pathlib.Path(__file__).parent.joinpath("roles.yml").read_text()
)
_roles_definitions = {
    role["name"]: RoleCreate.model_validate(role)
    for role in _roles_definitions_raw["roles"]
}


PLATFORM_MANAGER_ROLE = _roles_definitions[PLATFORM_MANAGER_ROLE_NAME]
PLATFORM_CREATOR_ROLE = _roles_definitions[PLATFORM_CREATOR_ROLE_NAME]
ORG_OWNER_ROLE = _roles_definitions[ORG_OWNER_ROLE_NAME]
ORG_EDITOR_ROLE = _roles_definitions[ORG_EDITOR_ROLE_NAME]
ORG_VIEWER_ROLE = _roles_definitions[ORG_VIEWER_ROLE_NAME]
PROJECT_OWNER_ROLE = _roles_definitions[PROJECT_OWNER_ROLE_NAME]
PROJECT_EDITOR_ROLE = _roles_definitions[PROJECT_EDITOR_ROLE_NAME]
PROJECT_VIEWER_ROLE = _roles_definitions[PROJECT_VIEWER_ROLE_NAME]
NA_ROLE = _roles_definitions[NA_ROLE_NAME]


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


if __name__ == "__main__":
    print(f"There are {len(ALL_ROLES)} pre-defined roles")
