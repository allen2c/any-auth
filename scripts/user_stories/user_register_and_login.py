# scripts/user_stories/user_register_and_login.py
# use server-side
import json
import logging
import os
import sys
import typing
from typing import Any, Dict, Optional

import faker
import httpx
import requests
from logging_bullet_train import set_logger
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from str_or_none import str_or_none

from any_auth.logger_name import LOGGER_NAME
from any_auth.types.oauth2 import TokenRequest, TokenResponse
from any_auth.types.user import User

logger = logging.getLogger(__name__)
console = Console()


VERBOSE = "--verbose" in sys.argv
SHORT_OUTPUT = "--short" in sys.argv or "-s" in sys.argv

if VERBOSE:
    set_logger(logger, level=logging.DEBUG)
    set_logger(LOGGER_NAME, level=logging.DEBUG)

FAKE: faker.Faker = faker.Faker()

BASE_URL = httpx.URL("http://localhost:8000")

TEST_USERNAME: str = "test_" + FAKE.user_name()
TEST_EMAIL: str = FAKE.email()
TEST_PASSWORD: str = FAKE.password()

ROPC_CLIENT_ID = str_or_none(os.getenv("ROPC_CLIENT_ID", "ropc_login_client"))
ROPC_CLIENT_SECRET = str_or_none(os.getenv("ROPC_CLIENT_SECRET"))
assert ROPC_CLIENT_ID is not None, "ROPC_CLIENT_ID is not set"
assert ROPC_CLIENT_SECRET is not None, "ROPC_CLIENT_SECRET is not set"


# === API Interaction Functions ===
def register_user(
    base_url: httpx.URL | str, username: str, email: str, password: str
) -> Optional[Dict[str, Any]]:
    """Registers a new user via the /public/register endpoint."""
    print_step("User Registration")
    url = f"{base_url}/public/register"
    payload = {
        "username": username,
        "email": email,
        "password": password,
    }
    print_request("POST", url, payload)
    try:
        response = requests.post(url, json=payload)
        print_response(response)
        response.raise_for_status()
        console.print("[bold green]Registration successful.[/bold green]")
        return response.json()
    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Registration failed:[/bold red] {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                console.print(f"[red]Error details:[/red] {e.response.json()}")
            except json.JSONDecodeError:
                console.print(f"[red]Error details:[/red] {e.response.text}")
        return None


def login_user(
    base_url: httpx.URL | str, username_or_email: str, password: str
) -> Optional[Dict[str, Any]]:
    """Logs in a user using the OAuth2 password flow."""
    print_step("User Login")
    url = f"{base_url}/oauth2/token"

    # Using OAuth2 password grant type
    payload = TokenRequest.model_validate(
        {
            "grant_type": "password",
            "username": username_or_email,  # Can be username or email
            "password": password,
            "scope": "openid profile email",  # Request standard OIDC scopes
            "client_id": ROPC_CLIENT_ID,
            "client_secret": ROPC_CLIENT_SECRET,
        }
    )

    print_request("POST", url, payload.model_dump(exclude_none=True))
    try:
        # Send as form data using the 'data' parameter
        response = requests.post(url, data=payload.model_dump(exclude_none=True))
        print_response(response)
        response.raise_for_status()
        console.print("[bold green]Login successful.[/bold green]")
        return response.json()  # Expected to return OAuth2 token response
    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Login failed:[/bold red] {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                console.print(f"[red]Error details:[/red] {e.response.json()}")
            except json.JSONDecodeError:
                console.print(f"[red]Error details:[/red] {e.response.text}")
        return None


def refresh_access_token(
    base_url: httpx.URL | str, refresh_token_value: str
) -> Optional[TokenResponse]:
    """Refreshes the access token using the OAuth2 refresh_token grant type."""
    print_step("Token Refresh")
    url = f"{base_url}/oauth2/token"
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token_value,
        "client_id": "ropc_login_client",  # This should match a configured client
    }

    print_request("POST", url, payload)

    try:
        # Send as form data
        response = requests.post(url, data=payload)
        print_response(response)
        response.raise_for_status()

        console.print("[bold green]Token refresh successful.[/bold green]")

        return TokenResponse.model_validate(
            response.json()
        )  # Should return a new OAuth2 token response

    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Token refresh failed:[/bold red] {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                console.print(f"[red]Error details:[/red] {e.response.json()}")
            except json.JSONDecodeError:
                console.print(f"[red]Error details:[/red] {e.response.text}")
        return None


def get_user_info_oidc(
    base_url: httpx.URL | str, access_token: str
) -> Optional[Dict[str, Any]]:
    """Gets user information from the standard OIDC /userinfo endpoint."""
    print_step("Get User Info (OIDC /userinfo)")
    url = f"{base_url}/oauth2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}

    print_request("GET", url, headers=headers)

    try:
        response = requests.get(url, headers=headers)
        print_response(response)
        response.raise_for_status()

        success_msg = (
            "[bold green]Successfully fetched user info via /userinfo.[/bold green]"
        )
        console.print(success_msg)

        return response.json()  # Returns claims based on token scope
    except requests.exceptions.RequestException as e:
        console.print(
            f"[bold red]Fetching user info via /userinfo failed:[/bold red] {e}"
        )
        if hasattr(e, "response") and e.response is not None:
            try:
                console.print(f"[red]Error details:[/red] {e.response.json()}")
            except json.JSONDecodeError:
                console.print(f"[red]Error details:[/red] {e.response.text}")
        return None


def get_user_info_me(base_url: httpx.URL | str, access_token: str) -> Optional[User]:
    """Gets user information from the custom /me endpoint."""

    print_step("Get User Info (/me endpoint)")
    url = f"{base_url}/me"
    headers = {"Authorization": f"Bearer {access_token}"}
    print_request("GET", url, headers=headers)

    try:
        response = requests.get(url, headers=headers)
        print_response(response)
        response.raise_for_status()
        console.print(
            "[bold green]Successfully fetched user info via /me.[/bold green]"
        )
        return User.model_validate(response.json())  # Returns User model

    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Fetching user info via /me failed:[/bold red] {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                console.print(f"[red]Error details:[/red] {e.response.json()}")
            except json.JSONDecodeError:
                console.print(f"[red]Error details:[/red] {e.response.text}")
        return None


def logout_user(base_url: httpx.URL | str, access_token: str) -> bool:
    """Logs out the user by revoking the token using the OAuth2 revocation endpoint."""
    print_step("User Logout")
    url = f"{base_url}/oauth2/revoke"

    # Standard OAuth2 token revocation request
    payload = {
        "token": access_token,
        "token_type_hint": "access_token",
        "client_id": ROPC_CLIENT_ID,
        "client_secret": ROPC_CLIENT_SECRET,
    }

    print_request("POST", url, payload=payload)

    try:
        # OAuth2 token revocation is always a POST with form data
        response = requests.post(url, data=payload)
        print_response(response)

        # OAuth2 token revocation should return 200 OK even if token wasn't found
        if response.status_code == 200:
            console.print("[bold green]Logout successful (token revoked).[/bold green]")
            return True

        else:
            response.raise_for_status()  # Raise exception for other errors
            return False

    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Logout failed:[/bold red] {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                console.print(f"[red]Error details:[/red] {e.response.json()}")
            except json.JSONDecodeError:
                console.print(f"[red]Error details:[/red] {e.response.text}")
        return False


# === End of API Interaction Functions ===


# === Helper Functions ===
def peek_token(token: str, length: int = 15) -> str:
    """Peeks at the first and last length characters of a token."""
    return token[:length] + "..." + token[-length:]


def print_step(title: typing.Text) -> None:
    """Prints a formatted step title."""
    console.print()
    console.print(
        Panel(f"[bold blue]{title}[/bold blue]", border_style="blue", expand=False)
    )


def print_request(
    method: str,
    url: str,
    payload: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> None:
    """Prints request details."""
    console.print(
        f"[bold cyan]>>> Sending [yellow]{method}[/yellow] "
        f"request to:[/bold cyan] [green]{url}[/green]"
    )
    if payload:
        # Mask password in logs
        if "password" in payload:
            payload_log = {**payload, "password": "***"}
        else:
            payload_log = payload
        console.print("    [bold]Payload:[/bold]", JSON.from_data(payload_log))
    if headers:
        # Mask Authorization header in logs
        headers_log = {**headers}
        if "Authorization" in headers_log:
            headers_log["Authorization"] = peek_token(headers_log["Authorization"])
        console.print("    [bold]Headers:[/bold]", JSON.from_data(headers_log))


def print_response(response: requests.Response) -> None:
    """Prints response details."""
    status_style = "green" if response.ok else "red"
    console.print(
        f"[bold cyan]<<< Received response:[/bold cyan] "
        f"Status Code [bold {status_style}]{response.status_code}[/bold {status_style}]"
    )
    try:
        console.print(
            "    [bold]Response Body:[/bold]", JSON.from_data(response.json())
        )
    except json.JSONDecodeError:
        console.print(f"    [bold]Response Body:[/bold] (Not JSON) {response.text}")
    console.print("[dim]" + "-" * 40 + "[/dim]")


# === End of Helper Functions ===


def main() -> None:
    """Runs the full user story."""
    panel = Panel.fit(
        "[bold magenta]User Auth Flow Simulation[/bold magenta]", border_style="magenta"
    )
    console.print(panel)
    console.print(
        f"Starting user story simulation against: [bold green]{BASE_URL}[/bold green]"
    )
    console.print(
        f"Using [bold]Username:[/bold] [blue]{TEST_USERNAME}[/blue], "
        f"[bold]Email:[/bold] [blue]{TEST_EMAIL}[/blue]"
    )

    # 1. Register User
    registration_result: Optional[Dict[str, Any]] = register_user(
        BASE_URL, TEST_USERNAME, TEST_EMAIL, TEST_PASSWORD
    )
    if not registration_result:
        console.print(
            "[bold red]Stopping simulation due to registration failure.[/bold red]"
        )
        return

    # Give the system a moment (optional, can help if there's eventual consistency)
    console.print("[yellow]Press Enter to continue...[/yellow]")
    input("\n\n")

    # 2. Login User
    login_result: Optional[Dict[str, Any]] = login_user(
        BASE_URL, TEST_EMAIL, TEST_PASSWORD
    )  # Login using email
    if not login_result:
        console.print("[bold red]Stopping simulation due to login failure.[/bold red]")
        return

    initial_access_token: Optional[str] = login_result.get("access_token")
    refresh_token_value: Optional[str] = login_result.get("refresh_token")

    if not initial_access_token or not refresh_token_value:
        console.print(
            "[bold red]Login response did not contain expected tokens.[/bold red]"
        )
        console.print("[bold red]Stopping simulation.[/bold red]")
        return

    console.print("\n[bold]Received initial tokens:[/bold]")
    console.print(
        f"  [blue]Access Token[/blue] (start): {peek_token(initial_access_token)}"
    )
    console.print(
        f"  [blue]Refresh Token[/blue] (start): {peek_token(refresh_token_value)}"
    )

    console.print("[yellow]Press Enter to continue...[/yellow]")
    input("\n\n")

    # 3. Get User Info with Initial Token
    user_info_oidc: Optional[Dict[str, Any]] = get_user_info_oidc(
        BASE_URL, initial_access_token
    )
    if user_info_oidc:
        console.print(
            "[bold]User Info from /userinfo:[/bold]", JSON.from_data(user_info_oidc)
        )

    user_info_me: Optional[User] = get_user_info_me(BASE_URL, initial_access_token)
    if user_info_me:
        console.print(
            "[bold]User Info from /me:[/bold]",
            JSON.from_data(user_info_me.model_dump()),
        )

    console.print("[yellow]Press Enter to continue...[/yellow]")
    input("\n\n")

    # 4. Refresh Token
    refresh_result: Optional[TokenResponse] = refresh_access_token(
        BASE_URL, refresh_token_value
    )
    if not refresh_result:
        console.print(
            "[bold red]Stopping simulation due to token refresh failure.[/bold red]"
        )
        return

    new_access_token = refresh_result.access_token
    # Note: The refresh token might or might not be rotated depending on server config.
    # Here we assume it might stay the same or be reissued.
    new_refresh_token = refresh_result.refresh_token or refresh_token_value

    if not new_access_token:
        console.print(
            "[bold red]Refresh response did not contain a new access token.[/bold red]"
        )
        console.print("[bold red]Stopping simulation.[/bold red]")
        return

    console.print("\n[bold]Received new token after refresh:[/bold]")
    console.print(f"  [blue]New Access Token[/blue]: {peek_token(new_access_token)}")

    if refresh_token_value != new_refresh_token:
        console.print(
            f"  [blue]New Refresh Token[/blue]: {peek_token(new_refresh_token)}"
        )
        console.print("[bold cyan]Note: Refresh token has been rotated[/bold cyan]")

    console.print("[yellow]Press Enter to continue...[/yellow]")
    input("\n\n")

    # 5. Get User Info with *New* Token
    attempt_msg = (
        "\n[bold cyan]Attempting to get user info with the NEW access token..."
    )
    attempt_msg += "[/bold cyan]"
    console.print(attempt_msg)
    user_info_oidc_new: Optional[Dict[str, Any]] = get_user_info_oidc(
        BASE_URL, new_access_token
    )
    if user_info_oidc_new:
        console.print(
            "[bold]User Info from /userinfo (New Token):[/bold]",
            JSON.from_data(user_info_oidc_new),
        )

    user_info_me_new: Optional[User] = get_user_info_me(BASE_URL, new_access_token)
    if user_info_me_new:
        console.print(
            "[bold]User Info from /me (New Token):[/bold]",
            JSON.from_data(user_info_me_new.model_dump()),
        )

    console.print("[yellow]Press Enter to continue...[/yellow]")
    input("\n\n")

    # 6. Logout (revoke the *new* token)
    logout_user(BASE_URL, new_access_token)

    # Optional: Try using the revoked token again to show it fails
    blacklist_msg = "\n[bold yellow]Attempting to use the revoked token..."
    blacklist_msg += "[/bold yellow]"
    console.print(blacklist_msg)
    get_user_info_oidc(BASE_URL, new_access_token)  # Expect this to fail with 401
    get_user_info_me(BASE_URL, new_access_token)  # Expect this to fail with 401

    console.print("\n[bold green]User story simulation finished.[/bold green]")

    console.print("[yellow]Press Enter to exit...[/yellow]")
    input("\n\n")


if __name__ == "__main__":
    main()
