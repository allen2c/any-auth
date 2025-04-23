"""
Google OAuth2 verification utilities.
"""

import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

# Google's token info endpoint
GOOGLE_TOKEN_INFO_URL = "https://oauth2.googleapis.com/tokeninfo"


async def verify_google_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify a Google OAuth token by calling Google's token verification endpoint.

    Args:
        token: The Google access token or ID token to verify

    Returns:
        Dict with user information if valid, None if invalid
    """
    try:
        # Try first as an ID token
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{GOOGLE_TOKEN_INFO_URL}?id_token={token}")

        if response.status_code == 200:
            return response.json()

        # If that fails, try as an access token
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{GOOGLE_TOKEN_INFO_URL}?access_token={token}")

        if response.status_code == 200:
            return response.json()

        logger.warning(f"Invalid Google token. Status: {response.status_code}")
        return None

    except Exception as e:
        logger.error(f"Error verifying Google token: {e}")
        return None
