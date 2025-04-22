# any_auth/utils/jwt_tokens.py
import logging
import time
import typing
import uuid

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa

from any_auth.config import Settings
from any_auth.types.oauth2 import OAuth2Token

logger = logging.getLogger(__name__)


def generate_jwt_access_token(
    user_id: str,
    client_id: str,
    scope: str,
    settings: Settings,
    expires_in: int | None = None,
    jti: str | None = None,
) -> str:
    """
    Generate a JWT format access token with proper claims and signing.

    Args:
        user_id: The user identifier (sub claim)
        client_id: The client identifier (aud claim)
        scope: Space-separated OAuth scopes
        settings: Application settings containing JWT configuration
        expires_in: Token lifetime in seconds (defaults to settings value)
        jti: Unique JWT ID (defaults to a generated UUID)

    Returns:
        A signed JWT token string
    """
    now = int(time.time())
    expiration = now + (expires_in or settings.TOKEN_EXPIRATION_TIME)

    # Build standard JWT claims
    claims = {
        "iss": f"https://{settings.ENVIRONMENT}.anyauth.example.com",  # Issuer
        "sub": user_id,  # Subject
        "aud": client_id,  # Audience
        "exp": expiration,  # Expiration
        "iat": now,  # Issued at
        "jti": jti or str(uuid.uuid4()),  # JWT ID
        "scope": scope,  # OAuth scopes
    }

    headers: typing.Dict[str, str] = {}
    if settings.JWT_KID:
        headers["kid"] = settings.JWT_KID

    # Sign the JWT with the configured secret and algorithm
    token = jwt.encode(
        claims,
        settings.private_key.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
        headers=headers,
    )

    return token


def verify_jwt_access_token(
    token: str,
    settings: Settings,
) -> dict:
    """
    Verify and decode a JWT access token.
    """
    # 1. Get the public key PEM string from settings and convert it to bytes
    public_pem = settings.public_key.get_secret_value().encode("utf-8")

    # 2. Use cryptography to load the PEM bytes as a public key object
    #    For RSA, this will be an RSAPublicKey object, which has a .verify() method
    public_key_obj = serialization.load_pem_public_key(public_pem)
    public_key_obj = typing.cast(
        typing.Union[
            rsa.RSAPublicKey,
            ec.EllipticCurvePublicKey,
        ],
        public_key_obj,
    )

    # 3. Pass the loaded public key object to jwt.decode
    claims = jwt.decode(
        token,
        public_key_obj,
        algorithms=[settings.JWT_ALGORITHM],
        options={"verify_aud": False},
    )
    return claims


def convert_oauth2_token_to_jwt(
    token: OAuth2Token,
    settings: Settings,
) -> OAuth2Token:
    """
    Convert a standard OAuth2Token to use JWT format for the access token.

    Args:
        token: The original token object
        settings: Application settings

    Returns:
        A new token object with a JWT access token
    """
    # Generate a JWT for the access token
    jwt_token = generate_jwt_access_token(
        user_id=token.user_id,
        client_id=token.client_id,
        scope=token.scope,
        settings=settings,
        expires_in=token.expires_at - int(time.time()),
        jti=token.id,
    )

    # Create a new token with JWT access token
    updated_token = OAuth2Token(
        id=token.id,
        access_token=jwt_token,
        refresh_token=token.refresh_token,
        token_type=token.token_type,
        scope=token.scope,
        expires_at=token.expires_at,
        user_id=token.user_id,
        client_id=token.client_id,
        issued_at=token.issued_at,
        revoked=token.revoked,
        authorization_code_id=token.authorization_code_id,
        device_id=token.device_id,
        ip_address=token.ip_address,
        user_agent=token.user_agent,
    )

    return updated_token
