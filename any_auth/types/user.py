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
    password: typing.Text = pydantic.Field(
        ...,
        min_length=8,
        max_length=64,
    )
    metadata: typing.Dict[typing.Text, typing.Any] = pydantic.Field(
        default_factory=dict
    )

    @pydantic.field_validator("password")
    def validate_password(cls, v: typing.Text) -> typing.Text:
        import fastapi

        from any_auth.utils.auth import is_valid_password

        if not is_valid_password(v):
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters and at most 64 characters long and contain at least one uppercase letter, one lowercase letter, one digit, and one special character.",  # noqa: E501
            )
        return v

    def to_user_in_db(self) -> UserInDB:
        from any_auth.utils.auth import hash_password

        data: typing.Dict = json.loads(self.model_dump_json())
        data["hashed_password"] = hash_password(data.pop("password"))
        return UserInDB.model_validate(data)


class UserUpdate(pydantic.BaseModel):
    full_name: typing.Text | None = pydantic.Field(default=None)
    email: pydantic.EmailStr | None = pydantic.Field(default=None)
    phone: typing.Text | None = pydantic.Field(default=None)
    metadata: typing.Dict[typing.Text, typing.Any] | None = pydantic.Field(default=None)
