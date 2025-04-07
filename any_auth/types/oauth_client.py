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

    # OAuth 2.0 specific fields
    client_type: typing.Literal["confidential", "public"] = "confidential"
    allowed_grant_types: typing.List[
        typing.Literal[
            "authorization_code",
            "implicit",
            "password",
            "client_credentials",
            "refresh_token",
        ]
    ] = pydantic.Field(default_factory=lambda: ["authorization_code", "refresh_token"])
    allowed_response_types: typing.List[typing.Literal["code", "token", "id_token"]] = (
        pydantic.Field(default_factory=lambda: ["code"])
    )
    allowed_scopes: typing.List[str] = pydantic.Field(default_factory=list)
    require_pkce: bool = False
    default_scopes: typing.List[str] = pydantic.Field(default_factory=list)
    token_endpoint_auth_method: typing.Literal[
        "client_secret_basic", "client_secret_post", "none"
    ] = "client_secret_basic"

    def to_oauth_client(self) -> "OAuthClient":
        client_id = secrets.token_urlsafe(24)
        client_secret = (
            secrets.token_urlsafe(48) if self.client_type == "confidential" else None
        )

        oauth_client = OAuthClient(
            client_id=client_id,
            client_secret=client_secret,
            name=self.name,
            redirect_uris=self.redirect_uris,
            scopes=self.scopes,
            project_id=self.project_id,
            client_type=self.client_type,
            allowed_grant_types=self.allowed_grant_types,
            allowed_response_types=self.allowed_response_types,
            allowed_scopes=self.allowed_scopes,
            require_pkce=self.require_pkce,
            default_scopes=self.default_scopes,
            token_endpoint_auth_method=self.token_endpoint_auth_method,
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

    # OAuth 2.0 specific fields
    client_type: typing.Literal["confidential", "public"] = "confidential"
    allowed_grant_types: typing.List[
        typing.Literal[
            "authorization_code",
            "implicit",
            "password",
            "client_credentials",
            "refresh_token",
        ]
    ] = pydantic.Field(default_factory=lambda: ["authorization_code", "refresh_token"])
    allowed_response_types: typing.List[typing.Literal["code", "token", "id_token"]] = (
        pydantic.Field(default_factory=lambda: ["code"])
    )
    allowed_scopes: typing.List[str] = pydantic.Field(default_factory=list)
    require_pkce: bool = False
    default_scopes: typing.List[str] = pydantic.Field(default_factory=list)
    token_endpoint_auth_method: typing.Literal[
        "client_secret_basic", "client_secret_post", "none"
    ] = "client_secret_basic"

    # For storing in Mongo, you can add a `_id` field if needed:
    _id: str | None = pydantic.PrivateAttr(default=None)

    def is_grant_type_allowed(self, grant_type: str) -> bool:
        """Check if the grant type is allowed for this client."""
        return grant_type in self.allowed_grant_types

    def is_response_type_allowed(self, response_type: str) -> bool:
        """Check if the response type is allowed for this client."""
        return response_type in self.allowed_response_types

    def validate_scopes(self, scopes: typing.List[str]) -> typing.List[str]:
        """
        Validate and filter requested scopes against allowed scopes.

        Returns:
            List of valid scopes
        """
        if not self.allowed_scopes:
            # No restrictions if allowed_scopes is empty
            return scopes

        # Filter out scopes that are not allowed
        return [scope for scope in scopes if scope in self.allowed_scopes]
