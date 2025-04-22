# scripts/user_stories/example_client_app.py
# uvicorn scripts.user_stories.example_client_app:app --port 5173 --reload
import base64
import json
import os
import secrets
import urllib.parse

import faker
import httpx
import requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from rich.console import Console
from str_or_none import str_or_none

from any_auth.api.oauth2 import TokenRequest, TokenResponse
from any_auth.types.user import User

console = Console()

AUTH_SERVER = "http://localhost:8000"
REDIRECT_URI = "http://localhost:5173/callback"
SCOPES = "openid profile email"

FAKE: faker.Faker = faker.Faker()

TEST_USERNAME: str = "test_" + FAKE.user_name()
TEST_EMAIL: str = FAKE.email()
TEST_PASSWORD: str = FAKE.password()

CLIENT_ID = str_or_none(os.getenv("CLIENT_ID", "test_application_client"))
CLIENT_SECRET = str_or_none(os.getenv("CLIENT_SECRET"))
assert CLIENT_ID is not None, "CLIENT_ID is not set"
assert CLIENT_SECRET is not None, "CLIENT_SECRET is not set"
CLIENT_BASIC_AUTH = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()


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


def login_user(
    base_url: httpx.URL | str, username_or_email: str, password: str
) -> TokenResponse:
    """Logs in a user using the OAuth2 password flow."""
    url = f"{base_url}/oauth2/token"

    # Using OAuth2 password grant type
    payload = TokenRequest.model_validate(
        {
            "grant_type": "password",
            "username": username_or_email,  # Can be username or email
            "password": password,
            "scope": "openid profile email",  # Request standard OIDC scopes
        }
    )

    headers = {"Authorization": f"Basic {CLIENT_BASIC_AUTH}"}

    response = requests.post(
        url, data=payload.model_dump(exclude_none=True), headers=headers
    )

    response.raise_for_status()

    return TokenResponse.model_validate(response.json())


TEST_USER = register_user(
    base_url=AUTH_SERVER,
    username=TEST_USERNAME,
    email=TEST_EMAIL,
    password=TEST_PASSWORD,
)
TEST_TOKEN = login_user(
    base_url=AUTH_SERVER, username_or_email=TEST_USERNAME, password=TEST_PASSWORD
)
console.rule("[bold green]Test User Registration[/bold green]")
console.print(
    json.dumps(TEST_USER.model_dump(), indent=4), style="cyan", highlight=True
)
console.rule("[bold green]Test User Token[/bold green]")
console.print(
    json.dumps(TEST_TOKEN.model_dump(), indent=4), style="magenta", highlight=True
)


# === Application ===

app = FastAPI()
_sessions: dict[str, dict[str, str]] = {}  # state ► {code_verifier, nonce}


@app.get("/login")
async def login():
    state = secrets.token_urlsafe(16)
    verifier = secrets.token_urlsafe(64)
    challenge = verifier  # demo uses plain

    nonce = secrets.token_urlsafe(16)

    # Store verifier / nonce, will be used later in callback
    _sessions[state] = {"verifier": verifier, "nonce": nonce}

    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,  # "openid profile email"
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "plain",
        "nonce": nonce,  # <── added this line
    }
    url = f"{AUTH_SERVER}/oauth2/authorize?" + urllib.parse.urlencode(params)

    # Still use programmatic fetch to preserve Authorization header
    async with httpx.AsyncClient(follow_redirects=False) as client:
        resp = await client.get(
            url, headers={"Authorization": f"Bearer {TEST_TOKEN.access_token}"}
        )
        location = resp.headers["location"]

    return RedirectResponse(location)


@app.get("/callback")
async def callback(request: Request, state: str, code: str):
    verifier = _sessions.pop(state)["verifier"]

    async with httpx.AsyncClient() as client:
        token = await client.post(
            f"{AUTH_SERVER}/oauth2/token",
            data={
                "grant_type": "authorization_code",
                "client_id": CLIENT_ID,
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "code_verifier": verifier,
            },
            headers={"Authorization": f"Basic {CLIENT_BASIC_AUTH}"},
        )
    payload = token.json()
    pretty_json = json.dumps(payload, indent=4)
    html = f"""
    <html>
        <head>
            <title>OAuth2 Callback Result</title>
            <style>
                body {{
                    background: #222;
                    color: #eee;
                    font-family: 'Fira Mono', 'Consolas', monospace;
                    padding: 2em;
                }}
                pre {{
                    background: #2d2d2d;
                    color: #a9dc76;
                    padding: 1em;
                    border-radius: 8px;
                    font-size: 1.1em;
                    overflow-x: auto;
                }}
                h2 {{
                    color: #82aaff;
                }}
            </style>
        </head>
        <body>
            <h2>OAuth2 Token Response</h2>
            <pre>{pretty_json}</pre>
        </body>
    </html>
    """
    return HTMLResponse(html)
