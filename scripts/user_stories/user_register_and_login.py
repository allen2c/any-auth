# user_register_and_login.py
import json
import typing
import uuid
from typing import Any, Dict, Optional

import faker
import requests

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
    print("\n" + "=" * 40)
    print(f"STEP: {title}")
    print("=" * 40)


def print_request(
    method: str,
    url: str,
    payload: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> None:
    """Prints request details."""
    print(f">>> Sending {method} request to: {url}")
    if payload:
        # Mask password in logs
        if "password" in payload:
            payload_log = {**payload, "password": "***"}
        else:
            payload_log = payload
        print(f"    Payload: {json.dumps(payload_log)}")
    if headers:
        # Mask Authorization header in logs
        headers_log = {**headers}
        if "Authorization" in headers_log:
            headers_log["Authorization"] = headers_log["Authorization"][:15] + "...***"
        print(f"    Headers: {json.dumps(headers_log)}")


def print_response(response: requests.Response) -> None:
    """Prints response details."""
    print(f"<<< Received response: Status Code {response.status_code}")
    try:
        print(f"    Response Body: {json.dumps(response.json(), indent=2)}")
    except json.JSONDecodeError:
        print(f"    Response Body: (Not JSON) {response.text}")
    print("-" * 40)


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
        print("Registration successful.")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Registration failed: {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                print(f"Error details: {e.response.json()}")
            except json.JSONDecodeError:
                print(f"Error details: {e.response.text}")
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
        print("Login successful.")
        return response.json()  # Expected to return Token model
    except requests.exceptions.RequestException as e:
        print(f"Login failed: {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                print(f"Error details: {e.response.json()}")
            except json.JSONDecodeError:
                print(f"Error details: {e.response.text}")
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
        print("Token refresh successful.")
        return response.json()  # Should return a new Token model
    except requests.exceptions.RequestException as e:
        print(f"Token refresh failed: {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                print(f"Error details: {e.response.json()}")
            except json.JSONDecodeError:
                print(f"Error details: {e.response.text}")
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
        print("Successfully fetched user info via /userinfo.")
        return response.json()  # Returns claims based on token scope
    except requests.exceptions.RequestException as e:
        print(f"Fetching user info via /userinfo failed: {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                print(f"Error details: {e.response.json()}")
            except json.JSONDecodeError:
                print(f"Error details: {e.response.text}")
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
        print("Successfully fetched user info via /me.")
        return response.json()  # Returns User model
    except requests.exceptions.RequestException as e:
        print(f"Fetching user info via /me failed: {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                print(f"Error details: {e.response.json()}")
            except json.JSONDecodeError:
                print(f"Error details: {e.response.text}")
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
            print("Logout successful (token likely blacklisted).")
            return True
        else:
            response.raise_for_status()  # Raise exception for other errors
            return False  # Should not be reached if status is not 204
    except requests.exceptions.RequestException as e:
        print(f"Logout failed: {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                print(f"Error details: {e.response.json()}")
            except json.JSONDecodeError:
                print(f"Error details: {e.response.text}")
        return False


# --- Main Execution Flow ---


def main() -> None:
    """Runs the full user story."""
    print(f"Starting user story simulation against: {BASE_URL}")
    print(f"Using Username: {TEST_USERNAME}, Email: {TEST_EMAIL}")

    # 1. Register User
    registration_result: Optional[Dict[str, Any]] = register_user(
        BASE_URL, TEST_USERNAME, TEST_EMAIL, TEST_PASSWORD
    )
    if not registration_result:
        print("Stopping simulation due to registration failure.")
        return

    # Give the system a moment (optional, can help if there's eventual consistency)
    input("Press Enter to continue...")

    # 2. Login User
    login_result: Optional[Dict[str, Any]] = login_user(
        BASE_URL, TEST_EMAIL, TEST_PASSWORD
    )  # Login using email
    if not login_result:
        print("Stopping simulation due to login failure.")
        return

    initial_access_token: Optional[str] = login_result.get("access_token")
    refresh_token_value: Optional[str] = login_result.get("refresh_token")

    if not initial_access_token or not refresh_token_value:
        print("Login response did not contain expected tokens.")
        print("Stopping simulation.")
        return

    print("\nReceived initial tokens:")
    print(f"  Access Token (start): {initial_access_token[:15]}...")
    print(f"  Refresh Token (start): {refresh_token_value[:15]}...")

    input("Press Enter to continue...")

    # 3. Get User Info with Initial Token
    user_info_oidc: Optional[Dict[str, Any]] = get_user_info_oidc(
        BASE_URL, initial_access_token
    )
    if user_info_oidc:
        print(f"User Info from /userinfo: {json.dumps(user_info_oidc, indent=2)}")

    user_info_me: Optional[Dict[str, Any]] = get_user_info_me(
        BASE_URL, initial_access_token
    )
    if user_info_me:
        print(f"User Info from /me: {json.dumps(user_info_me, indent=2)}")

    input("Press Enter to continue...")

    # 4. Refresh Token
    refresh_result: Optional[Dict[str, Any]] = refresh_access_token(
        BASE_URL, refresh_token_value
    )
    if not refresh_result:
        print("Stopping simulation due to token refresh failure.")
        return

    new_access_token: Optional[str] = refresh_result.get("access_token")
    # Note: The refresh token might or might not be rotated depending on server config.
    # Here we assume it might stay the same or be reissued.
    # new_refresh_token = refresh_result.get("refresh_token")

    if not new_access_token:
        print("Refresh response did not contain a new access token.")
        print("Stopping simulation.")
        return

    print("\nReceived new token after refresh:")
    print(f"  New Access Token: {new_access_token[:15]}...")

    input("Press Enter to continue...")

    # 5. Get User Info with *New* Token
    print("\nAttempting to get user info with the NEW access token...")
    user_info_oidc_new: Optional[Dict[str, Any]] = get_user_info_oidc(
        BASE_URL, new_access_token
    )
    if user_info_oidc_new:
        print(
            f"User Info from /userinfo (New Token): {json.dumps(user_info_oidc_new, indent=2)}"  # noqa: E501
        )

    user_info_me_new: Optional[Dict[str, Any]] = get_user_info_me(
        BASE_URL, new_access_token
    )
    if user_info_me_new:
        print(
            f"User Info from /me (New Token): {json.dumps(user_info_me_new, indent=2)}"
        )

    input("Press Enter to continue...")

    # 6. Logout (blacklist the *new* token)
    logout_user(BASE_URL, new_access_token)

    # Optional: Try using the blacklisted token again to show it fails
    print("\nAttempting to use the logged-out (potentially blacklisted) token...")
    get_user_info_me(BASE_URL, new_access_token)  # Expect this to fail with 401

    print("\nUser story simulation finished.")

    input("Press Enter to exit...")


if __name__ == "__main__":
    main()
