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
