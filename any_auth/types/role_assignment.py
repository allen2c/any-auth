import json
import time
import typing
import uuid

import pydantic

if typing.TYPE_CHECKING:
    from any_auth.backend import BackendClient

PLATFORM_ID: typing.Final[typing.Text] = "platform"


class RoleAssignment(pydantic.BaseModel):
    id: typing.Text = pydantic.Field(default_factory=lambda: str(uuid.uuid4()))
    target_id: typing.Text
    role_id: typing.Text
    resource_id: typing.Text = pydantic.Field(
        ...,
        description=(
            "The ID of the organization, project or resource to assign the role to."
            "If the resource_id is the platform ID, the role will be assigned to the user globally."  # noqa: E501
        ),
    )
    assigned_at: int = pydantic.Field(default_factory=lambda: int(time.time()))

    _id: typing.Text | None = pydantic.PrivateAttr(default=None)

    def to_doc(self) -> typing.Dict[typing.Text, typing.Any]:
        return json.loads(self.model_dump_json())


RoleAssignmentList: typing.TypeAlias = list[RoleAssignment]
RoleAssignmentListAdapter = pydantic.TypeAdapter(RoleAssignmentList)


class RoleAssignmentCreate(pydantic.BaseModel):
    target_id: typing.Text
    role_id: typing.Text
    resource_id: typing.Text

    def to_role_assignment(self) -> RoleAssignment:
        return RoleAssignment(
            target_id=self.target_id,
            role_id=self.role_id,
            resource_id=self.resource_id,
        )


class MemberRoleAssignmentCreate(pydantic.BaseModel):
    role: typing.Text

    def to_role_assignment_create(
        self,
        *,
        backend_client: "BackendClient",
        target_id: typing.Text,
        resource_id: typing.Text,
    ) -> RoleAssignmentCreate:
        import fastapi

        role_name_or_id = self.role
        role = backend_client.roles.retrieve_by_name(role_name_or_id)
        if not role:
            role = backend_client.roles.retrieve(role_name_or_id)
        if not role:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail="Role not found",
            )

        return RoleAssignmentCreate(
            target_id=target_id,
            role_id=role.id,
            resource_id=resource_id,
        )
