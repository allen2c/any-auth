"""
OpenID Connect endpoints for AnyAuth.

Implements core OIDC functionality:
- Discovery endpoint (.well-known/openid-configuration)
- UserInfo endpoint (authenticated user information)
"""

# any_auth/api/oidc.py
# use OAuth
import asyncio
import logging
import typing

import fastapi
from authlib.jose import JsonWebKey
from authlib.jose.rfc7518.ec_key import ECKey
from authlib.jose.rfc7518.rsa_key import RSAKey
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa

import any_auth.deps.app_state as AppState
from any_auth.backend import BackendClient
from any_auth.config import Settings
from any_auth.deps.auth import requires_scope, validate_oauth2_token
from any_auth.types.oidc import JWKSet, OpenIDConfiguration

logger = logging.getLogger(__name__)

router = fastapi.APIRouter(tags=["OpenID Connect"])


@router.get("/oauth2/.well-known/jwks.json", response_model=JWKSet)
async def jwks_uri(settings: Settings = fastapi.Depends(AppState.depends_settings)):
    """
    JSON Web Key Set endpoint.
    Returns the public key(s) used for signing JWTs in JWK format.
    """
    try:
        public_key_str = settings.public_key.get_secret_value()
        public_pem = public_key_str.encode("utf-8")

        if settings.JWT_ALGORITHM == "RS256":
            public_key_obj = serialization.load_pem_public_key(public_pem)
        elif settings.JWT_ALGORITHM == "ES256":
            public_key_obj = serialization.load_pem_public_key(public_pem)
        else:
            raise fastapi.HTTPException(
                status_code=500, detail="Unsupported JWT algorithm"
            )

        public_key_obj = typing.cast(
            typing.Union[
                rsa.RSAPublicKey,
                ec.EllipticCurvePublicKey,
            ],
            public_key_obj,
        )

        # 1. Use JsonWebKey.import_key to import the cryptography key object
        jwk_instance: typing.Union[RSAKey, ECKey] = JsonWebKey.import_key(public_pem)

        # 2. Convert the JWK instance to a dictionary, including necessary
        # header information as_dict will handle kty, n, e (for RSA)
        # or crv, x, y (for EC), etc.
        jwk_data = jwk_instance.as_dict(
            kid=settings.JWT_KID,
            use="sig",
            alg=settings.JWT_ALGORITHM,
        )

        # JWK Set format is a JSON object containing a "keys" list
        return JWKSet.model_validate({"keys": [jwk_data]})

    except Exception as e:
        logger.error(f"Error generating JWK Set: {e}", exc_info=True)
        raise fastapi.HTTPException(
            status_code=500, detail="Could not generate JWK Set"
        )


@router.get(
    "/oauth2/.well-known/openid-configuration",
    response_model=OpenIDConfiguration,
)
async def openid_configuration(
    request: fastapi.Request,
    settings: Settings = fastapi.Depends(AppState.depends_settings),
):
    """
    OpenID Connect Discovery endpoint.

    Returns the server's capabilities according to the OpenID Connect Discovery specification.
    """  # noqa: E501
    base_url = str(request.base_url).rstrip("/")

    # Build the OpenID Provider Metadata
    config = {
        "issuer": f"{base_url}",
        "authorization_endpoint": f"{base_url}/oauth2/authorize",
        "token_endpoint": f"{base_url}/oauth2/token",
        "userinfo_endpoint": f"{base_url}/oauth2/userinfo",
        "jwks_uri": f"{base_url}/oauth2/.well-known/jwks.json",  # Add JWK Set URI
        "id_token_signing_alg_values_supported": [
            settings.JWT_ALGORITHM
        ],  # Update supported algorithms
        "token_endpoint_auth_signing_alg_values_supported": [
            settings.JWT_ALGORITHM
        ],  # If the token endpoint also requires signature verification
        "response_types_supported": [
            "code",
            "token",
            "id_token",
            "code token",
            "code id_token",
            "token id_token",
            "code token id_token",
        ],
        "subject_types_supported": ["public"],
        "scopes_supported": [
            "openid",
            "profile",
            "email",
            "address",
            "phone",
            "offline_access",
        ],
        "token_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "client_secret_post",
        ],
        "claims_supported": [
            "sub",
            "iss",
            "auth_time",
            "name",
            "given_name",
            "family_name",
            "preferred_username",
            "email",
            "email_verified",
            "locale",
            "picture",
            "zoneinfo",
            "updated_at",
        ],
        "grant_types_supported": [
            "authorization_code",
            "implicit",
            "refresh_token",
            "password",
            "client_credentials",
        ],
        "service_documentation": f"{base_url}/docs",
        "revocation_endpoint": f"{base_url}/oauth2/revoke",
        "introspection_endpoint": f"{base_url}/oauth2/introspect",
    }

    return OpenIDConfiguration.model_validate(config)


@router.get("/oauth2/userinfo", include_in_schema=True)
async def userinfo_endpoint(
    token_data: dict = fastapi.Depends(validate_oauth2_token),
    has_scope: bool = fastapi.Depends(requires_scope("openid")),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    """
    OpenID Connect UserInfo endpoint.

    Returns claims about the authenticated user.
    Requires a valid access token with 'openid' scope.
    """
    # Extract user_id from token data
    user_id = token_data.get("sub")
    if not user_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token - missing subject claim",
        )

    # Retrieve user from database
    user = await asyncio.to_thread(backend_client.users.retrieve, user_id)
    if not user:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Check if user is active
    if user.disabled:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    # Determine which claims to include based on scopes
    scopes = token_data.get("scope", "").split()

    # Build the claims object
    claims: typing.Dict[str, typing.Any] = {
        "sub": user.id,  # Subject identifier - required
    }

    # Add profile claims if requested
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

    # Add email claims if requested
    if "email" in scopes:
        claims.update(
            {
                "email": user.email,
                "email_verified": user.email_verified,
            }
        )

    # Add phone claims if requested
    if "phone" in scopes:
        claims.update(
            {
                "phone_number": user.phone,
                "phone_number_verified": user.phone_verified,
            }
        )

    # Add address claims if requested
    if "address" in scopes and user.address:
        claims.update(
            {
                "address": {
                    "formatted": user.address,
                }
            }
        )

    return claims
