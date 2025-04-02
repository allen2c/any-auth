# any_auth/types/oauth_client.py
import secrets
import time
import typing
import uuid

import pydantic


class OAuthClientCreate(pydantic.BaseModel):
    name: typing.Text
    redirect_uris: typing.List[pydantic.HttpUrl]
    scopes: typing.List[str] = pydantic.Field(default_factory=list)
    project_id: typing.Optional[str] = None

    def to_oauth_client(self) -> "OAuthClient":
        client_id = secrets.token_urlsafe(24)
        client_secret = secrets.token_urlsafe(48)

        oauth_client = OAuthClient(
            client_id=client_id,
            client_secret=client_secret,
            name=self.name,
            redirect_uris=self.redirect_uris,
            scopes=self.scopes,
            project_id=self.project_id,
        )
        return oauth_client


class OAuthClient(pydantic.BaseModel):
    """
    Represents a registered OAuth client (public or confidential).
    """

    id: str = pydantic.Field(default_factory=lambda: str(uuid.uuid4()))
    client_id: str
    client_secret: typing.Optional[str] = None  # For confidential clients
    name: str
    redirect_uris: typing.List[pydantic.HttpUrl] = pydantic.Field(default_factory=list)
    scopes: typing.List[str] = pydantic.Field(default_factory=list)
    project_id: typing.Optional[str] = None
    created_at: int = pydantic.Field(default_factory=lambda: int(time.time()))
    disabled: bool = pydantic.Field(default=False)

    # For storing in Mongo, you can add a `_id` field if needed:
    _id: str | None = pydantic.PrivateAttr(default=None)
