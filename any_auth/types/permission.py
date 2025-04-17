import enum
import pathlib
import typing
from types import MappingProxyType

import pydantic
import yaml


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

    @classmethod
    def all(cls) -> list["Permission"]:
        return list(cls)


class PermissionDefinition(pydantic.BaseModel):
    name: Permission | typing.Text
    description: typing.Text = pydantic.Field(default="")


_permissions_definitions_raw = yaml.safe_load(
    pathlib.Path(__file__).parent.joinpath("permissions.yml").read_text()
)
PERMISSIONS_DEFINITIONS: typing.Final[
    MappingProxyType[typing.Text, PermissionDefinition]
] = MappingProxyType(
    {
        permission["name"]: PermissionDefinition.model_validate(permission)
        for permission in _permissions_definitions_raw["permissions"]
    }
)
ALL_PERMISSIONS: typing.Final[typing.List[typing.Text]] = list(
    PERMISSIONS_DEFINITIONS.keys()
)
