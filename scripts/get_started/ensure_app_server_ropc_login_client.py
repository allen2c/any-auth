# scripts/get_started/ensure_app_server_ropc_login_client.py
# use server

import logging
import sys

from logging_bullet_train import set_logger
from rich.console import Console
from rich.json import JSON as RichJSON
from rich.text import Text as RichText

from any_auth.backend import BackendClient, BackendSettings
from any_auth.config import Settings
from any_auth.logger_name import LOGGER_NAME
from any_auth.types.oauth_client import OAuthClient, OAuthClientCreate

# Setup logging
logger = logging.getLogger(__name__)
console = Console()

CUSTOM_CLIENT_NAME = "ROPC Login Client"
CUSTOM_CLIENT_ID = "ropc_login_client"

# Command line arguments
VERBOSE = "--verbose" in sys.argv
SHORT_OUTPUT = "--short" in sys.argv or "-s" in sys.argv

if VERBOSE:
    set_logger(logger, level=logging.DEBUG)
    set_logger(LOGGER_NAME, level=logging.DEBUG)


def create_server_ropc_login_client(backend_client: BackendClient) -> OAuthClient:
    """Create a Resource Owner Password Credentials login client."""
    req_body = OAuthClientCreate.model_validate(
        {
            "name": CUSTOM_CLIENT_NAME,
            "redirect_uris": ["http://localhost:3000/callback"],
            "allowed_grant_types": ["password", "refresh_token"],
            "allowed_scopes": ["openid", "profile", "email", "offline_access"],
            "client_type": "confidential",
        }
    )

    oauth_client = backend_client.oauth_clients.create(
        req_body, client_id=CUSTOM_CLIENT_ID
    )

    return oauth_client


def display_client_info(client: OAuthClient) -> None:
    """Display client information with rich formatting."""

    if SHORT_OUTPUT:
        print(f"{client.client_id}:{client.client_secret}")
    else:
        console.print(RichText("Client Created Successfully", style="bold magenta"))
        console.print(RichText(f"Client ID: {client.client_id}", style="bold green"))
        console.print(
            RichText(f"Client Secret: {client.client_secret}", style="bold cyan")
        )
        console.print(RichText("Full Client Details:", style="bold"))
        console.print(RichJSON(client.model_dump_json(indent=4)))


def main():
    settings = Settings()  # type: ignore

    backend_client = BackendClient.from_settings(
        settings, backend_settings=BackendSettings.from_any_auth_settings(settings)
    )
    logger.info(f"Connected to database: '{backend_client.database_url}'")

    client = create_server_ropc_login_client(backend_client)
    display_client_info(client)


if __name__ == "__main__":
    main()
