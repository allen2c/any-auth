import json
import time
import typing
import uuid

import pydantic

from any_auth.types.role_assignment import RoleAssignment


class User(pydantic.BaseModel):
    id: typing.Text = pydantic.Field(default_factory=lambda: str(uuid.uuid4()))
    username: typing.Text = pydantic.Field(
        ..., pattern=r"^[a-zA-Z0-9_-]+$", min_length=4, max_length=64
    )
    full_name: typing.Text | None = pydantic.Field(default=None)
    email: pydantic.EmailStr | None = pydantic.Field(default=None)
    phone: typing.Text | None = pydantic.Field(default=None)
    disabled: bool = pydantic.Field(default=False)
    metadata: typing.Dict[typing.Text, typing.Any] = pydantic.Field(
        default_factory=dict
    )
    created_at: int = pydantic.Field(default_factory=lambda: int(time.time()))
    updated_at: int = pydantic.Field(default_factory=lambda: int(time.time()))

    _id: typing.Text | None = pydantic.PrivateAttr(default=None)
    _role_assignments: typing.List[RoleAssignment] | None = pydantic.PrivateAttr(
        default=None
    )

    def to_doc(self) -> typing.Dict[typing.Text, typing.Any]:
        return json.loads(self.model_dump_json())


class UserInDB(User):
    hashed_password: typing.Text


class UserCreate(pydantic.BaseModel):
    username: typing.Text = pydantic.Field(
        ..., pattern=r"^[a-zA-Z0-9_-]+$", min_length=4, max_length=64
    )
    full_name: typing.Text | None = pydantic.Field(default=None)
    email: pydantic.EmailStr | None = pydantic.Field(default=None)
    phone: typing.Text | None = pydantic.Field(default=None)
    password: typing.Text
    metadata: typing.Dict[typing.Text, typing.Any] = pydantic.Field(
        default_factory=dict
    )


class UserUpdate(pydantic.BaseModel):
    full_name: typing.Text | None = pydantic.Field(default=None)
    email: pydantic.EmailStr | None = pydantic.Field(default=None)
    phone: typing.Text | None = pydantic.Field(default=None)
    metadata: typing.Dict[typing.Text, typing.Any] | None = pydantic.Field(default=None)
