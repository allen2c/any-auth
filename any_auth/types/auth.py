import typing

import pydantic


class AuthTokenRequest(pydantic.BaseModel):
    provider: typing.Text
    email: typing.Text
    name: typing.Text
    picture: typing.Text
    googleId: typing.Text | None = pydantic.Field(default=None)
