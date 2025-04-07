"""
OAuth 2.0 utility functions for AnyAuth.
"""

import hashlib
import logging
import secrets
import urllib.parse

logger = logging.getLogger(__name__)


def generate_authorization_code() -> str:
    """Generate a secure random authorization code."""
    return secrets.token_urlsafe(48)


def generate_token() -> str:
    """Generate a secure random token."""
    return secrets.token_urlsafe(48)


def generate_refresh_token() -> str:
    """Generate a secure random refresh token."""
    return secrets.token_urlsafe(64)


def build_redirect_uri(
    redirect_uri: str,
    params: dict[str, str],
) -> str:
    """
    Build a redirect URI with query parameters.

    Args:
        redirect_uri: The base redirect URI
        params: Query parameters to add

    Returns:
        The complete redirect URI with query parameters
    """
    parsed_uri = urllib.parse.urlparse(redirect_uri)

    # Get existing query parameters
    existing_params = urllib.parse.parse_qs(parsed_uri.query)

    # Merge with new parameters
    all_params = {**existing_params, **params}

    # Build new query string
    query_string = urllib.parse.urlencode(all_params, doseq=True)

    # Construct new parts with updated query
    parts = list(parsed_uri)
    parts[4] = query_string

    # Return the rebuilt URI
    return urllib.parse.urlunparse(parts)


def build_error_redirect(
    redirect_uri: str,
    error: str,
    error_description: str | None = None,
    state: str | None = None,
) -> str:
    """
    Build an error redirect URI according to OAuth 2.0 spec.

    Args:
        redirect_uri: The client's redirect URI
        error: OAuth 2.0 error code
        error_description: Optional error description
        state: State parameter from the authorization request

    Returns:
        The error redirect URI
    """
    params = {"error": error}

    if error_description:
        params["error_description"] = error_description

    if state:
        params["state"] = state

    return build_redirect_uri(redirect_uri, params)


def calculate_code_challenge(verifier: str, method: str) -> str:
    """
    Calculate a PKCE code challenge from a code verifier.

    Args:
        verifier: The code verifier
        method: The challenge method ("plain" or "S256")

    Returns:
        The calculated code challenge
    """
    if method == "plain":
        return verifier

    if method == "S256":
        challenge = hashlib.sha256(verifier.encode()).digest()
        return challenge.hex()

    raise ValueError(f"Unsupported code challenge method: {method}")


def verify_code_challenge(
    verifier: str,
    challenge: str,
    method: str,
) -> bool:
    """
    Verify a PKCE code challenge against a verifier.

    Args:
        verifier: The code verifier to check
        challenge: The code challenge to verify against
        method: The challenge method used

    Returns:
        True if the challenge is valid, False otherwise
    """
    calculated = calculate_code_challenge(verifier, method)
    return calculated == challenge


def validate_redirect_uri(client_redirect_uris: list[str], redirect_uri: str) -> bool:
    """
    Validate that a redirect URI is allowed for a client.

    Args:
        client_redirect_uris: List of allowed redirect URIs for the client
        redirect_uri: The redirect URI to validate

    Returns:
        True if the redirect URI is allowed, False otherwise
    """
    # Exact match
    if redirect_uri in client_redirect_uris:
        return True

    # Parse the redirect URI
    parsed_redirect_uri = urllib.parse.urlparse(redirect_uri)

    # Check if any of the allowed URIs match the base part
    for allowed_uri in client_redirect_uris:
        parsed_allowed_uri = urllib.parse.urlparse(allowed_uri)

        # Compare scheme, netloc, and path
        if (
            parsed_redirect_uri.scheme == parsed_allowed_uri.scheme
            and parsed_redirect_uri.netloc == parsed_allowed_uri.netloc
            and parsed_redirect_uri.path == parsed_allowed_uri.path
        ):
            return True

    return False


def parse_scope(scope: str) -> list[str]:
    """
    Parse a space-delimited scope string into a list of individual scopes.

    Args:
        scope: Space-delimited scope string

    Returns:
        List of individual scopes
    """
    if not scope:
        return []

    return [s.strip() for s in scope.split() if s.strip()]


def scope_to_string(scopes: list[str]) -> str:
    """
    Convert a list of scopes to a space-delimited string.

    Args:
        scopes: List of scopes

    Returns:
        Space-delimited scope string
    """
    return " ".join(scopes)
