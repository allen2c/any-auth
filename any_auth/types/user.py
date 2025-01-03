import time
import typing
import uuid

import pydantic


class User(pydantic.BaseModel):
    id: typing.Text = pydantic.Field(default_factory=lambda: str(uuid.uuid4()))
    username: typing.Text = pydantic.Field(
        ..., pattern=r"^[a-zA-Z0-9_-]+$", min_length=4, max_length=32
    )
    name: typing.Text | None = pydantic.Field(default=None)
    email: pydantic.EmailStr | None = pydantic.Field(default=None)
    phone: typing.Text | None = pydantic.Field(default=None)
    created_at: int = pydantic.Field(default_factory=lambda: int(time.time()))
    updated_at: int = pydantic.Field(default_factory=lambda: int(time.time()))
    metadata: typing.Dict[typing.Text, typing.Any] = pydantic.Field(
        default_factory=dict
    )

    _id: typing.Text | None = pydantic.PrivateAttr(default=None)


class UserInDB(User):
    hashed_password: typing.Text


class UserCreate(pydantic.BaseModel):
    username: typing.Text = pydantic.Field(
        ..., pattern=r"^[a-zA-Z0-9_-]+$", min_length=4, max_length=32
    )
    name: typing.Text | None = pydantic.Field(default=None)
    email: pydantic.EmailStr | None = pydantic.Field(default=None)
    phone: typing.Text | None = pydantic.Field(default=None)
    password: typing.Text
    metadata: typing.Dict[typing.Text, typing.Any] = pydantic.Field(
        default_factory=dict
    )


class UserUpdate(pydantic.BaseModel):
    name: typing.Text | None = pydantic.Field(default=None)
    email: pydantic.EmailStr | None = pydantic.Field(default=None)
    phone: typing.Text | None = pydantic.Field(default=None)
    metadata: typing.Dict[typing.Text, typing.Any] | None = pydantic.Field(default=None)
