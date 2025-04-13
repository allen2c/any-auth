# user_register_and_login.py
import json
import typing
import uuid
from typing import Any, Dict, Optional

import faker
import requests
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel

# Initialize Rich console
console = Console()

FAKE: faker.Faker = faker.Faker()

# --- Configuration ---
# !!! UPDATE THIS to your running server's URL !!!
BASE_URL: str = "http://localhost:8000"
# Use unique details for each run to avoid registration conflicts
UNIQUE_ID: str = str(uuid.uuid4()).split("-")[0]
TEST_USERNAME: str = "test_" + FAKE.user_name()
TEST_EMAIL: str = FAKE.email()
# Password must meet complexity requirements (adjust if needed)
# any-auth default: >=8 chars, 1 upper, 1 lower, 1 digit, 1 special
TEST_PASSWORD: str = FAKE.password()

# --- Helper Functions ---


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
            headers_log["Authorization"] = headers_log["Authorization"][:15] + "...***"
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


# --- API Interaction Functions ---


def register_user(
    base_url: str, username: str, email: str, password: str
) -> Optional[Dict[str, Any]]:
    """Registers a new user via the /users endpoint."""
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
    base_url: str, username_or_email: str, password: str
) -> Optional[Dict[str, Any]]:
    """Logs in a user via the /login endpoint using OAuth2PasswordRequestForm."""
    print_step("User Login")
    url = f"{base_url}/login"
    # This endpoint expects form data, not JSON
    payload = {
        "username": username_or_email,  # Can be username or email
        "password": password,
        # grant_type is implicitly 'password' for OAuth2PasswordRequestForm
    }
    print_request("POST", url, payload)
    try:
        # Send as form data using the 'data' parameter
        response = requests.post(url, data=payload)
        print_response(response)
        response.raise_for_status()
        console.print("[bold green]Login successful.[/bold green]")
        return response.json()  # Expected to return Token model
    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Login failed:[/bold red] {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                console.print(f"[red]Error details:[/red] {e.response.json()}")
            except json.JSONDecodeError:
                console.print(f"[red]Error details:[/red] {e.response.text}")
        return None


def refresh_access_token(
    base_url: str, refresh_token_value: str
) -> Optional[Dict[str, Any]]:
    """Refreshes the access token using the /refresh endpoint."""
    print_step("Token Refresh")
    url = f"{base_url}/refresh"
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token_value,
    }
    print_request("POST", url, payload)
    try:
        # Send as form data
        response = requests.post(url, data=payload)
        print_response(response)
        response.raise_for_status()
        console.print("[bold green]Token refresh successful.[/bold green]")
        return response.json()  # Should return a new Token model
    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Token refresh failed:[/bold red] {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                console.print(f"[red]Error details:[/red] {e.response.json()}")
            except json.JSONDecodeError:
                console.print(f"[red]Error details:[/red] {e.response.text}")
        return None


def get_user_info_oidc(base_url: str, access_token: str) -> Optional[Dict[str, Any]]:
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


def get_user_info_me(base_url: str, access_token: str) -> Optional[Dict[str, Any]]:
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
        return response.json()  # Returns User model
    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Fetching user info via /me failed:[/bold red] {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                console.print(f"[red]Error details:[/red] {e.response.json()}")
            except json.JSONDecodeError:
                console.print(f"[red]Error details:[/red] {e.response.text}")
        return None


def logout_user(base_url: str, access_token: str) -> bool:
    """Logs out the user by calling the /logout endpoint (blacklists token)."""
    print_step("User Logout")
    url = f"{base_url}/logout"
    headers = {"Authorization": f"Bearer {access_token}"}
    print_request("POST", url, headers=headers)
    try:
        # The logout endpoint might expect the token via header and not need a body
        response = requests.post(url, headers=headers)
        print_response(response)
        # Expecting 204 No Content on successful logout/blacklisting
        if response.status_code == 204:
            logout_msg = (
                "[bold green]Logout successful (token likely blacklisted).[/bold green]"
            )
            console.print(logout_msg)
            return True
        else:
            response.raise_for_status()  # Raise exception for other errors
            return False  # Should not be reached if status is not 204
    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Logout failed:[/bold red] {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                console.print(f"[red]Error details:[/red] {e.response.json()}")
            except json.JSONDecodeError:
                console.print(f"[red]Error details:[/red] {e.response.text}")
        return False


# --- Main Execution Flow ---


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
    input()

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
        f"  [blue]Access Token[/blue] (start): {initial_access_token[:15]}..."
    )
    console.print(
        f"  [blue]Refresh Token[/blue] (start): {refresh_token_value[:15]}..."
    )

    console.print("[yellow]Press Enter to continue...[/yellow]")
    input()

    # 3. Get User Info with Initial Token
    user_info_oidc: Optional[Dict[str, Any]] = get_user_info_oidc(
        BASE_URL, initial_access_token
    )
    if user_info_oidc:
        console.print(
            "[bold]User Info from /userinfo:[/bold]", JSON.from_data(user_info_oidc)
        )

    user_info_me: Optional[Dict[str, Any]] = get_user_info_me(
        BASE_URL, initial_access_token
    )
    if user_info_me:
        console.print("[bold]User Info from /me:[/bold]", JSON.from_data(user_info_me))

    console.print("[yellow]Press Enter to continue...[/yellow]")
    input()

    # 4. Refresh Token
    refresh_result: Optional[Dict[str, Any]] = refresh_access_token(
        BASE_URL, refresh_token_value
    )
    if not refresh_result:
        console.print(
            "[bold red]Stopping simulation due to token refresh failure.[/bold red]"
        )
        return

    new_access_token: Optional[str] = refresh_result.get("access_token")
    # Note: The refresh token might or might not be rotated depending on server config.
    # Here we assume it might stay the same or be reissued.
    # new_refresh_token = refresh_result.get("refresh_token")

    if not new_access_token:
        console.print(
            "[bold red]Refresh response did not contain a new access token.[/bold red]"
        )
        console.print("[bold red]Stopping simulation.[/bold red]")
        return

    console.print("\n[bold]Received new token after refresh:[/bold]")
    console.print(f"  [blue]New Access Token[/blue]: {new_access_token[:15]}...")

    console.print("[yellow]Press Enter to continue...[/yellow]")
    input()

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

    user_info_me_new: Optional[Dict[str, Any]] = get_user_info_me(
        BASE_URL, new_access_token
    )
    if user_info_me_new:
        console.print(
            "[bold]User Info from /me (New Token):[/bold]",
            JSON.from_data(user_info_me_new),
        )

    console.print("[yellow]Press Enter to continue...[/yellow]")
    input()

    # 6. Logout (blacklist the *new* token)
    logout_user(BASE_URL, new_access_token)

    # Optional: Try using the blacklisted token again to show it fails
    blacklist_msg = "\n[bold yellow]Attempting to use the logged-out token..."
    blacklist_msg += "[/bold yellow]"
    console.print(blacklist_msg)
    get_user_info_me(BASE_URL, new_access_token)  # Expect this to fail with 401

    console.print("\n[bold green]User story simulation finished.[/bold green]")

    console.print("[yellow]Press Enter to exit...[/yellow]")
    input()


if __name__ == "__main__":
    main()
