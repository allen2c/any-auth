import datetime
import typing
import zoneinfo

import pydantic


class Token(pydantic.BaseModel):
    access_token: typing.Text
    refresh_token: typing.Text
    token_type: typing.Text
    scope: typing.Text
    expires_at: int
    expires_in: int
    issued_at: typing.Text = pydantic.Field(
        default_factory=lambda: datetime.datetime.now(
            zoneinfo.ZoneInfo("UTC")
        ).isoformat()
    )
    meta: typing.Dict[typing.Text, typing.Any] = pydantic.Field(default_factory=dict)
