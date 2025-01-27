import json
import time
import typing
import uuid

import pydantic


class RoleAssignment(pydantic.BaseModel):
    id: typing.Text = pydantic.Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: typing.Text
    role_id: typing.Text
    resource_id: typing.Text = pydantic.Field(
        ...,
        description=(
            "The ID of the organization, project or resource to assign the role to"
        ),
    )
    assigned_at: int = pydantic.Field(default_factory=lambda: int(time.time()))

    _id: typing.Text | None = pydantic.PrivateAttr(default=None)

    def to_doc(self) -> typing.Dict[typing.Text, typing.Any]:
        return json.loads(self.model_dump_json())


class RoleAssignmentCreate(pydantic.BaseModel):
    user_id: typing.Text
    role_id: typing.Text
    resource_id: typing.Text

    def to_role_assignment(self) -> RoleAssignment:
        return RoleAssignment(
            user_id=self.user_id,
            role_id=self.role_id,
            resource_id=self.resource_id,
        )
