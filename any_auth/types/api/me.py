import typing

import pydantic

from any_auth.types.role import Permission, Role


class MePermissionsResponse(pydantic.BaseModel):
    resource_id: typing.Text
    user_id: typing.Text | None = None
    api_key_id: typing.Text | None = None
    roles: typing.List[Role] = pydantic.Field(default_factory=list)
    permissions: typing.List[Permission | typing.Text] = pydantic.Field(
        default_factory=list
    )
    details: typing.Dict[typing.Text, typing.Any] = pydantic.Field(default_factory=dict)


class MePermissionsEvaluateRequest(pydantic.BaseModel):
    resource_id: typing.Text
    permissions_to_check: typing.List[Permission | typing.Text] = pydantic.Field(
        default_factory=list
    )


class MePermissionsEvaluateResponse(pydantic.BaseModel):
    allowed: bool
    user_id: typing.Text | None = None
    api_key_id: typing.Text | None = None
    resource_id: typing.Text
    granted_permissions: typing.List[Permission | typing.Text] = pydantic.Field(
        default_factory=list
    )
    missing_permissions: typing.List[Permission | typing.Text] = pydantic.Field(
        default_factory=list
    )
    details: typing.Dict[typing.Text, typing.Any] = pydantic.Field(default_factory=dict)
