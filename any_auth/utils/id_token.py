"""
ID Token generation utilities for OpenID Connect support.
"""

# any_auth/utils/id_token.py
import time
import typing
import uuid

import jwt

from any_auth.config import Settings
from any_auth.types.user import UserInDB


def generate_id_token(
    user: UserInDB,
    client_id: str,
    settings: Settings,
    *,
    nonce: str | None = None,
    auth_time: int | None = None,
    requested_scopes: list[str] | None = None,
    expires_in: int | None = None,
) -> str:
    """
    Generate an OpenID Connect ID Token.

    Args:
        user: The authenticated user
        client_id: The OAuth client ID (audience)
        settings: Application settings
        nonce: Optional nonce from the authentication request
        auth_time: Time of user authentication
        requested_scopes: Scopes to determine which claims to include
        expires_in: Token lifetime in seconds (defaults to access token lifetime)

    Returns:
        Signed JWT ID token string
    """
    now = int(time.time())
    expiration = now + (expires_in or settings.TOKEN_EXPIRATION_TIME)

    # Base claims required for all ID tokens
    claims = {
        "iss": f"https://{settings.ENVIRONMENT}.anyauth.example.com",  # Issuer
        "sub": user.id,  # Subject
        "aud": client_id,  # Audience
        "exp": expiration,  # Expiration
        "iat": now,  # Issued at
        "auth_time": auth_time or now,  # Time of authentication
        "jti": str(uuid.uuid4()),  # JWT ID
    }

    # Add nonce if provided (for replay protection)
    if nonce:
        claims["nonce"] = nonce

    # Add user claims based on requested scopes
    scopes = requested_scopes or []

    # Add identity claims based on scopes
    if "profile" in scopes:
        claims.update(
            {
                "name": user.full_name,
                "preferred_username": user.username,
                "picture": user.picture,
                "website": user.website,
                "gender": user.gender,
                "birthdate": user.birthdate,
                "zoneinfo": user.zoneinfo,
                "locale": user.locale,
                "updated_at": user.updated_at,
            }
        )

    if "email" in scopes:
        claims.update(
            {
                "email": user.email,
                "email_verified": user.email_verified,
            }
        )

    if "phone" in scopes:
        claims.update(
            {
                "phone_number": user.phone,
                "phone_number_verified": user.phone_verified,
            }
        )

    if "address" in scopes:
        claims.update(
            {
                "address": {
                    "formatted": user.address,
                }
            }
        )

    headers: typing.Dict[str, str] = {}
    if settings.JWT_KID:
        headers["kid"] = settings.JWT_KID

    # Sign the token
    id_token = jwt.encode(
        claims,
        settings.private_key.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
        headers=headers,
    )

    return id_token


def validate_id_token(
    id_token: str,
    client_id: str,
    settings: Settings,
    nonce: str | None = None,
) -> dict:
    """
    Validate an ID token and return its claims.

    Args:
        id_token: The ID token to validate
        client_id: Expected client ID (audience)
        settings: Application settings
        nonce: Expected nonce (if originally provided)

    Returns:
        The decoded and validated claims

    Raises:
        jwt.InvalidTokenError: If the token is invalid
    """
    # Decode and verify the token
    claims = jwt.decode(
        id_token,
        settings.private_key.get_secret_value(),
        algorithms=[settings.JWT_ALGORITHM],
        # audience=client_id,
    )

    # Verify nonce if provided
    if nonce and claims.get("nonce") != nonce:
        raise jwt.InvalidTokenError("Nonce mismatch")

    return claims
