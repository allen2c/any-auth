import secrets
import time
import typing
import uuid

import pydantic


class Invite(pydantic.BaseModel):
    id: typing.Text = pydantic.Field(default_factory=lambda: str(uuid.uuid4()))
    resource_id: typing.Text
    email: pydantic.EmailStr
    invited_by: typing.Text  # User ID who created the invite
    created_at: int = pydantic.Field(default_factory=lambda: int(time.time()))
    expires_at: int  # Timestamp when the invite expires
    metadata: typing.Dict[typing.Text, typing.Text] = pydantic.Field(
        default_factory=dict
    )

    _id: typing.Text | None = pydantic.PrivateAttr(default=None)

    # To convert to dict/json for storing in Mongo
    def to_doc(self) -> typing.Dict[typing.Text, typing.Any]:
        return self.model_dump()


class InviteInDB(Invite):
    temporary_token: typing.Text


class InviteCreate(pydantic.BaseModel):
    email: pydantic.EmailStr
    metadata: typing.Dict[typing.Text, typing.Any] = pydantic.Field(
        default_factory=dict
    )

    def to_invite(
        self,
        resource_id: typing.Text,
        invited_by: typing.Text,
        expires_in: int = 15 * 60,
        temporary_token: typing.Text | None = None,
    ) -> InviteInDB:
        """
        Convert the create model to an Invite model
        """

        now = int(time.time())
        return InviteInDB(
            resource_id=resource_id,
            email=self.email,
            invited_by=invited_by,
            created_at=now,
            expires_at=now + expires_in,
            metadata=self.metadata,
            temporary_token=temporary_token or secrets.token_urlsafe(128),
        )
