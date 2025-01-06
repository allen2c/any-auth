import json
import time
import typing
import uuid

import pydantic

if typing.TYPE_CHECKING:
    from any_auth.types.project import Project


class Organization(pydantic.BaseModel):
    id: typing.Text = pydantic.Field(default_factory=lambda: str(uuid.uuid4()))
    name: typing.Text = pydantic.Field(
        ..., pattern=r"^[a-zA-Z0-9_-]+$", min_length=4, max_length=64
    )
    full_name: typing.Text | None = pydantic.Field(default=None)
    disabled: bool = pydantic.Field(default=False)
    metadata: typing.Dict[typing.Text, typing.Any] = pydantic.Field(
        default_factory=dict
    )
    created_at: int = pydantic.Field(default_factory=lambda: int(time.time()))
    updated_at: int = pydantic.Field(default_factory=lambda: int(time.time()))

    _id: typing.Text | None = pydantic.PrivateAttr(default=None)
    _projects: typing.Optional[typing.List["Project"]] = pydantic.PrivateAttr(
        default=None
    )

    def to_doc(self) -> typing.Dict[typing.Text, typing.Any]:
        return json.loads(self.model_dump_json())


class OrganizationCreate(pydantic.BaseModel):
    name: typing.Text
    full_name: typing.Text | None = pydantic.Field(default=None)
    metadata: typing.Dict[typing.Text, typing.Any] = pydantic.Field(
        default_factory=dict
    )

    def to_org(self) -> Organization:
        return Organization(
            name=self.name,
            full_name=self.full_name,
            metadata=self.metadata,
        )


class OrganizationUpdate(pydantic.BaseModel):
    full_name: typing.Text | None = pydantic.Field(default=None)
    metadata: typing.Dict[typing.Text, typing.Any] | None = pydantic.Field(default=None)
