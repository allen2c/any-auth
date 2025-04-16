"""
OAuth 2.0 models and types for AnyAuth.

Implements RFC 6749 (OAuth 2.0), RFC 7636 (PKCE), and related standards.
"""

import enum
import secrets
import time
import typing
import uuid

import pydantic


# Define standard OAuth2 grant types
class GrantType(str, enum.Enum):
    AUTHORIZATION_CODE = "authorization_code"
    IMPLICIT = "implicit"
    PASSWORD = "password"
    CLIENT_CREDENTIALS = "client_credentials"
    REFRESH_TOKEN = "refresh_token"


# Define standard OAuth2 response types
class ResponseType(str, enum.Enum):
    CODE = "code"
    TOKEN = "token"
    ID_TOKEN = "id_token"  # For OpenID Connect


# Define standard OAuth2 token types
class TokenType(str, enum.Enum):
    BEARER = "Bearer"
    MAC = "MAC"  # Less common


class CodeChallengeMethod(str, enum.Enum):
    """
    PKCE (RFC 7636) code challenge methods.
    """

    PLAIN = "plain"
    S256 = "S256"  # SHA-256


class OAuth2Error(str, enum.Enum):
    """
    Standard OAuth2 error codes as defined in RFC 6749.
    """

    INVALID_REQUEST = "invalid_request"
    INVALID_CLIENT = "invalid_client"
    INVALID_GRANT = "invalid_grant"
    UNAUTHORIZED_CLIENT = "unauthorized_client"
    UNSUPPORTED_GRANT_TYPE = "unsupported_grant_type"
    INVALID_SCOPE = "invalid_scope"
    ACCESS_DENIED = "access_denied"
    SERVER_ERROR = "server_error"
    TEMPORARILY_UNAVAILABLE = "temporarily_unavailable"
    UNSUPPORTED_RESPONSE_TYPE = "unsupported_response_type"


class AuthorizationRequest(pydantic.BaseModel):
    """
    OAuth2 authorization request parameters according to RFC 6749.
    """

    response_type: ResponseType
    client_id: str
    redirect_uri: pydantic.HttpUrl
    scope: str
    state: str | None = None

    # PKCE (RFC 7636) extension
    code_challenge: str | None = None
    code_challenge_method: CodeChallengeMethod | None = None

    # Additional parameters that might be supported
    prompt: typing.Literal["none", "login", "consent", "select_account"] | None = None
    nonce: str | None = None


class TokenRequest(pydantic.BaseModel):
    """
    OAuth2 token request parameters according to RFC 6749.
    """

    grant_type: GrantType

    # For authorization_code grant
    code: str | None = None
    redirect_uri: pydantic.HttpUrl | None = None
    code_verifier: str | None = None

    # For password grant
    username: str | None = None
    password: str | None = None

    # For refresh_token grant
    refresh_token: str | None = None

    # Common parameter
    scope: str | None = None


class TokenResponse(pydantic.BaseModel):
    """
    OAuth2 token response parameters according to RFC 6749 and OpenID Connect Core.
    """

    access_token: str
    token_type: TokenType = TokenType.BEARER
    expires_in: int
    refresh_token: str | None = None
    scope: str | None = None
    id_token: str | None = None  # OpenID Connect ID token


class ErrorResponse(pydantic.BaseModel):
    """
    OAuth2 error response parameters according to RFC 6749.
    """

    error: OAuth2Error
    error_description: str | None = None
    error_uri: str | None = None
    state: str | None = None


class AuthorizationCode(pydantic.BaseModel):
    """
    Model for storing authorization codes.
    """

    id: str = pydantic.Field(default_factory=lambda: str(uuid.uuid4()))
    code: str = pydantic.Field(default_factory=lambda: secrets.token_urlsafe(48))
    client_id: str
    redirect_uri: pydantic.HttpUrl
    scope: str
    user_id: str
    expires_at: int = pydantic.Field(
        default_factory=lambda: int(time.time()) + 600
    )  # 10 minutes
    used: bool = False

    # PKCE extension
    code_challenge: str | None = None
    code_challenge_method: CodeChallengeMethod | None = None

    # Additional metadata
    nonce: str | None = None
    auth_time: int = pydantic.Field(default_factory=lambda: int(time.time()))

    _id: str | None = pydantic.PrivateAttr(default=None)

    def is_expired(self) -> bool:
        """Check if the authorization code has expired."""
        return time.time() > self.expires_at

    def to_doc(self) -> dict[str, typing.Any]:
        """Convert to MongoDB document."""
        return self.model_dump()

    @property
    def has_pkce(self) -> bool:
        """Check if PKCE is being used with this authorization code."""
        return bool(self.code_challenge and self.code_challenge_method)


class OAuth2Token(pydantic.BaseModel):
    """
    Model for storing OAuth2 tokens.
    """

    id: str = pydantic.Field(default_factory=lambda: str(uuid.uuid4()))
    access_token: str = pydantic.Field(
        default_factory=lambda: secrets.token_urlsafe(48)
    )
    refresh_token: str | None = pydantic.Field(
        default_factory=lambda: secrets.token_urlsafe(64)
    )
    token_type: TokenType = TokenType.BEARER
    scope: str
    expires_at: int
    user_id: str
    client_id: str
    issued_at: int = pydantic.Field(default_factory=lambda: int(time.time()))
    revoked: bool = False

    # References
    authorization_code_id: str | None = None

    # Additional metadata
    device_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None

    _id: str | None = pydantic.PrivateAttr(default=None)

    def is_expired(self) -> bool:
        """Check if the access token has expired."""
        return time.time() > self.expires_at

    def to_doc(self) -> dict[str, typing.Any]:
        """Convert to MongoDB document."""
        return self.model_dump()


class TokenIntrospectionResponse(pydantic.BaseModel):
    """
    OAuth 2.0 token introspection response as defined in RFC 7662.
    """

    active: bool
    scope: str | None = None
    client_id: str | None = None
    username: str | None = None
    token_type: str | None = None
    exp: int | None = None
    iat: int | None = None
    nbf: int | None = None
    sub: str | None = None
    aud: str | None = None
    iss: str | None = None
    jti: str | None = None

    # Extension fields
    user_id: str | None = None
