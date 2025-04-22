# scripts/user_stories/decode_jwt.py
# use server-side
import base64
import json
import logging
import os
import sys
from functools import wraps

import faker
import httpx
import jwt
import jwt.algorithms
import requests
from logging_bullet_train import set_logger
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table
from str_or_none import str_or_none

from any_auth.logger_name import LOGGER_NAME
from any_auth.types.oauth2 import (
    TokenIntrospectionResponse,
    TokenRequest,
    TokenResponse,
)
from any_auth.types.oidc import JWK, JWKSet, OpenIDConfiguration
from any_auth.types.user import User

logger = logging.getLogger(__name__)
console = Console()


VERBOSE = "--verbose" in sys.argv

if VERBOSE:
    set_logger(logger, level=logging.DEBUG)
    set_logger(LOGGER_NAME, level=logging.DEBUG)

FAKE: faker.Faker = faker.Faker()

BASE_URL = httpx.URL("http://localhost:8000")

TEST_USERNAME: str = "test_" + FAKE.user_name()
TEST_EMAIL: str = FAKE.email()
TEST_PASSWORD: str = FAKE.password()

CLIENT_ID = str_or_none(os.getenv("CLIENT_ID", "test_application_client"))
CLIENT_SECRET = str_or_none(os.getenv("CLIENT_SECRET"))
assert CLIENT_ID is not None, "CLIENT_ID is not set"
assert CLIENT_SECRET is not None, "CLIENT_SECRET is not set"
CLIENT_BASIC_AUTH = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()


def server_side(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def client_side(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


@server_side
def register_user(
    base_url: httpx.URL | str, username: str, email: str, password: str
) -> User:
    """Registers a new user via the /public/register endpoint."""

    url = f"{base_url}/v1/users/register"
    payload = {
        "username": username,
        "email": email,
        "password": password,
    }
    headers = {"Authorization": f"Basic {CLIENT_BASIC_AUTH}"}

    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()

    return User.model_validate(response.json())


@server_side
def login_user(
    base_url: httpx.URL | str, username_or_email: str, password: str
) -> TokenResponse:
    """Logs in a user using the OAuth2 password flow."""

    url = f"{base_url}/oauth2/token"

    # Using OAuth2 password grant type
    payload = TokenRequest.model_validate(
        {
            "grant_type": "password",
            "username": username_or_email,
            "password": password,
            "scope": "openid profile email",
        }
    )

    headers = {"Authorization": f"Basic {CLIENT_BASIC_AUTH}"}

    # Send as form data using the 'data' parameter
    response = requests.post(
        url, data=payload.model_dump(exclude_none=True), headers=headers
    )
    response.raise_for_status()

    return TokenResponse.model_validate(response.json())


@server_side
def get_jwks(base_url: httpx.URL | str) -> JWKSet:
    """Gets the JWKS."""

    url = f"{base_url}/oauth2/.well-known/jwks.json"

    response = requests.get(url)
    response.raise_for_status()

    return JWKSet.model_validate(response.json())


@server_side
def get_openid_configuration(base_url: httpx.URL | str) -> OpenIDConfiguration:
    """Gets the OpenID configuration."""

    url = f"{base_url}/oauth2/.well-known/openid-configuration"

    response = requests.get(url)
    response.raise_for_status()

    return OpenIDConfiguration.model_validate(response.json())


@server_side
def introspect_jwt(
    openid_configuration: OpenIDConfiguration, token: str
) -> TokenIntrospectionResponse:
    """Decodes a JWT token."""

    url = openid_configuration.introspection_endpoint
    assert url is not None, "Introspection endpoint is not set"

    payload = {"token": token}
    headers = {"Authorization": f"Basic {CLIENT_BASIC_AUTH}"}

    response = requests.post(url, data=payload, headers=headers)
    response.raise_for_status()

    return TokenIntrospectionResponse.model_validate(response.json())


@server_side
def decode_jwt(jwks: JWKSet, token: str) -> dict:
    """
    Verify *and* decode a JWT using a JSON‑Web‑Key‑Set (JWKS).

    Example claims return format:
    {
        'iss': 'https://development.anyauth.example.com',
        'sub': '498b58cb-bac3-48dd-82b6-faf3bbf5c00b',
        'aud': 'test_application_client',
        'exp': 1745306119,
        'iat': 1745305219,
        'jti': 'ef257bb9-eccb-4727-a4b9-585dd078e6d4',
        'scope': 'openid profile email'
    }
    """

    # 1. Read the JOSE header without verifying the signature yet.
    header = jwt.get_unverified_header(token)
    kid: str | None = header.get("kid")
    alg: str = header.get("alg", "RS256")

    # 2. Pick the correct key from the supplied JWKS.
    chosen_jwk: JWK | None = None
    for _key in jwks.keys:
        if kid and _key.kid == kid:
            chosen_jwk = _key
            break
    else:
        # fall‑back: use the first key if the token has no kid
        if kid is None and jwks.keys:
            chosen_jwk = jwks.keys[0]

    if chosen_jwk is None:
        raise ValueError(
            "No matching JWK found for token header. "
            + f"header: {header}, jwks: {jwks}"
        )

    # 3. Build a usable public‑key object. PyJWT offers helpers per algorithm.
    if chosen_jwk.kty == "RSA":
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(chosen_jwk.model_dump())
    elif chosen_jwk.kty == "EC":
        public_key = jwt.algorithms.ECAlgorithm.from_jwk(chosen_jwk.model_dump())
    else:
        raise ValueError(f"Unsupported JWK kty: {chosen_jwk.kty}")

    # 4. Finally verify signature, exp/nbf/iat and return the claims.
    #    Audience/issuer checks are turned off here for generality; enable
    #    them in production with options or explicit parameters.
    claims: dict = jwt.decode(
        token,
        public_key,  # type: ignore
        algorithms=[alg],
        options={
            "verify_aud": False,
            "verify_iss": False,
        },
    )

    return claims


def display_user_info(user: User) -> None:
    """Display user information in a pretty table."""
    table = Table(title="User Information")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("ID", user.id)
    table.add_row("Username", user.username)
    table.add_row("Email", user.email)
    table.add_row("Created At", str(user.created_at))

    console.print(table)


def display_token_info(token_response: TokenResponse) -> None:
    """Display token information in a pretty table."""
    table = Table(title="Token Information")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Access Token", token_response.access_token[:20] + "...")
    table.add_row("Token Type", token_response.token_type)
    table.add_row("Expires In", str(token_response.expires_in))
    if token_response.refresh_token:
        table.add_row("Refresh Token", token_response.refresh_token[:20] + "...")
    if token_response.scope:
        table.add_row("Scope", token_response.scope)

    console.print(table)


def display_jwt_decoded(decoded_jwt: dict) -> None:
    """Display decoded JWT in a pretty panel with syntax highlighting."""
    formatted_json = json.dumps(decoded_jwt, indent=2)
    syntax = Syntax(formatted_json, "json", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title="Decoded JWT Token", border_style="green"))


def main() -> None:
    """Main function with pretty output."""
    console.print(Panel.fit("JWT Decoder Demo", style="bold blue"))

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold green]{task.description}"),
        console=console,
    ) as progress:
        task1 = progress.add_task("[cyan]Registering user...", total=1)

        user = register_user(
            base_url=BASE_URL,
            username=TEST_USERNAME,
            email=TEST_EMAIL,
            password=TEST_PASSWORD,
        )
        progress.update(task1, completed=1)

        console.line()
        display_user_info(user)
        console.line()

        task2 = progress.add_task("[cyan]Logging in user...", total=1)
        token_response = login_user(
            base_url=BASE_URL,
            username_or_email=user.email,
            password=TEST_PASSWORD,
        )
        progress.update(task2, completed=1)

        console.line()
        display_token_info(token_response)
        console.line()

        task3 = progress.add_task("[cyan]Getting JWKS and OpenID config...", total=1)
        jwks = get_jwks(BASE_URL)
        openid_configuration = get_openid_configuration(BASE_URL)
        progress.update(task3, completed=1)

        task4 = progress.add_task("[cyan]Introspecting and decoding JWT...", total=1)
        token_introspection = introspect_jwt(
            openid_configuration=openid_configuration,
            token=token_response.access_token,
        )

        decoded_jwt = decode_jwt(jwks=jwks, token=token_response.access_token)
        progress.update(task4, completed=1)

    console.line()
    display_jwt_decoded(decoded_jwt)
    console.line()

    # Verify sub values
    verified = (
        decoded_jwt["sub"] == user.id and decoded_jwt["sub"] == token_introspection.sub
    )
    if verified:
        rprint("[bold green]✓ Verification successful![/] Subject IDs match correctly")
    else:
        rprint("[bold red]× Verification failed![/] Subject IDs don't match")


if __name__ == "__main__":
    main()
