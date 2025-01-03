import time
import typing
import uuid

import pydantic


class Organization(pydantic.BaseModel):
    id: typing.Text = pydantic.Field(default_factory=lambda: str(uuid.uuid4()))
    organization_name: typing.Text = pydantic.Field(
        ..., pattern=r"^[a-zA-Z0-9_-]+$", min_length=4, max_length=64
    )
    name: typing.Text
    created_at: int = pydantic.Field(default_factory=lambda: int(time.time()))
    updated_at: int = pydantic.Field(default_factory=lambda: int(time.time()))
    metadata: typing.Dict[typing.Text, typing.Any] = pydantic.Field(
        default_factory=dict
    )

    _id: typing.Text | None = pydantic.PrivateAttr(default=None)


class OrganizationCreate(pydantic.BaseModel):
    organization_name: typing.Text
    name: typing.Text
    metadata: typing.Dict[typing.Text, typing.Any] = pydantic.Field(
        default_factory=dict
    )


class OrganizationUpdate(pydantic.BaseModel):
    name: typing.Text | None = pydantic.Field(default=None)
    metadata: typing.Dict[typing.Text, typing.Any] | None = pydantic.Field(default=None)
