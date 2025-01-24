import datetime
import json
import logging
import textwrap
import time
import typing
import zoneinfo

import fastapi
import jwt
from authlib.integrations.starlette_client import OAuth
from authlib.integrations.starlette_client.apps import StarletteOAuth2App

import any_auth.deps.app_state as AppState
import any_auth.utils.jwt_manager as JWTManager
from any_auth.backend import BackendClient
from any_auth.backend.users import UserCreate
from any_auth.config import Settings
from any_auth.types.oauth import SessionStateGoogleData, TokenUserInfo
from any_auth.types.token import Token
from any_auth.types.user import UserInDB

logger = logging.getLogger(__name__)

router = fastapi.APIRouter()


async def depends_session_active_user(
    request: fastapi.Request,
    settings: Settings = fastapi.Depends(AppState.depends_settings),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> UserInDB:
    session_user = request.session.get("user")
    session_token = request.session.get("token")
    if not session_user:
        logger.debug("User not found in session")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    if not session_token:
        logger.debug("Token not found in session")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    try:
        jwt_token = Token.model_validate(session_token)

        if time.time() > jwt_token.expires_at:
            logger.debug("Token expired")
            raise jwt.ExpiredSignatureError

        payload = JWTManager.verify_jwt_token(
            jwt_token.access_token,
            jwt_secret=settings.JWT_SECRET_KEY.get_secret_value(),
            jwt_algorithm=settings.JWT_ALGORITHM,
        )
        logger.debug(f"Payload: {payload}")
        JWTManager.raise_if_payload_expired(payload)
        user_id = JWTManager.get_user_id_from_payload(payload)
    except jwt.ExpiredSignatureError:
        logger.debug("Token expired")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED, detail="Token expired"
        )
    except jwt.InvalidTokenError:
        logger.debug("Invalid token")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
    except Exception as e:
        logger.exception(e)
        logger.error("Error during session active user")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

    if not user_id:
        logger.debug("User ID not found in payload")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    user_in_db = backend_client.users.retrieve(user_id)
    if not user_in_db:
        logger.debug("User not found in database")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    # Check session data match
    if user_in_db.email != session_user.get("email"):
        logger.debug(
            "User email in session does not match user email in database: "
            + f"{user_in_db.email} != {session_user.get('email')}"
        )
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    return user_in_db


@router.get("/auth")
async def auth_homepage(request: fastapi.Request):
    user = request.session.get("user")
    if user:
        return fastapi.responses.HTMLResponse(
            f"""
            <h1>Hello, {user['name']}!</h1>
            <img src="{user['picture']}">
            <p><a href="/auth/protected">Protected Route</a></p>
            <p><a href="/auth/logout">Logout</a></p>
        """
        )
    else:
        return fastapi.responses.HTMLResponse('<a href="/login">Login with Google</a>')


@router.get("/auth/token")
async def auth_token():
    raise fastapi.HTTPException(
        status_code=fastapi.status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented"
    )


@router.get("/auth/expired")
async def auth_expired():
    return fastapi.responses.HTMLResponse(
        textwrap.dedent(
            """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <title>Session Expired</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                        background-color: #f0f0f0;
                    }
                    .container {
                        text-align: center;
                        background-color: white;
                        padding: 2rem;
                        border-radius: 10px;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    }
                    .login-btn {
                        background-color: #4CAF50;
                        color: white;
                        border: none;
                        padding: 10px 20px;
                        text-decoration: none;
                        display: inline-block;
                        font-size: 16px;
                        margin-top: 20px;
                        cursor: pointer;
                        border-radius: 5px;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Session Expired</h1>
                    <p>Your session has expired. Please log in again.</p>
                    <a href="/auth/google/login" class="login-btn">Login with Google</a>
                </div>
            </body>
            </html>
            """
        ),
        status_code=fastapi.status.HTTP_410_GONE,
    )


@router.get("/auth/google/login")
async def login(
    request: fastapi.Request, oauth: OAuth = fastapi.Depends(AppState.depends_oauth)
):
    redirect_uri = request.url_for("auth")
    oauth_google = typing.cast(StarletteOAuth2App, oauth.google)
    return await oauth_google.authorize_redirect(request, redirect_uri)


@router.get("/auth/google/callback")
async def auth(
    request: fastapi.Request,
    oauth: OAuth = fastapi.Depends(AppState.depends_oauth),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
    settings: Settings = fastapi.Depends(AppState.depends_settings),
):
    logger.debug("--- Google Callback Started ---")  # Log start of callback
    logger.debug(f"Request URL: {request.url}")  # Log the full request URL
    logger.debug(f"Request Session: {request.session}")  # Log session data

    try:
        oauth_google = typing.cast(StarletteOAuth2App, oauth.google)
        session_state_google = SessionStateGoogleData.from_session(request.session)
        token = await oauth_google.authorize_access_token(request)
        user = await oauth_google.parse_id_token(
            token, nonce=session_state_google.data["nonce"]
        )
        user_info = TokenUserInfo.model_validate(user)
        logger.info(f"User parsed from ID Token: {user}")  # Log user info

        # Create user if not exists
        user_info.raise_if_not_name()
        user_info.raise_if_not_email()
        user_in_db = backend_client.users.retrieve_by_email(user_info.email)
        if not user_in_db:
            user_in_db = backend_client.users.create(
                UserCreate(
                    username=user_info.name,
                    full_name=user_info.given_name or user_info.name,
                    email=user_info.email,
                    phone=user_info.phone_number or None,
                    password=Settings.fake.password(),
                )
            )
            logger.info(f"User created: {user_in_db.id}: {user_in_db.username}")
        else:
            logger.debug(f"User already exists: {user_in_db.id}: {user_in_db.username}")

        # JWT Token
        _dt_now = datetime.datetime.now(zoneinfo.ZoneInfo("UTC"))
        _now = int(time.time())
        jwt_token = Token(
            access_token=JWTManager.create_jwt_token(
                user_id=user_in_db.id,
                expires_in=settings.TOKEN_EXPIRATION_TIME,
                jwt_secret=settings.JWT_SECRET_KEY.get_secret_value(),
                jwt_algorithm=settings.JWT_ALGORITHM,
                now=_now,
            ),
            refresh_token=JWTManager.create_jwt_token(
                user_id=user_in_db.id,
                expires_in=settings.REFRESH_TOKEN_EXPIRATION_TIME,
                jwt_secret=settings.JWT_SECRET_KEY.get_secret_value(),
                jwt_algorithm=settings.JWT_ALGORITHM,
                now=_now,
            ),
            token_type="Bearer",
            scope="openid email profile phone",
            expires_at=_now + settings.TOKEN_EXPIRATION_TIME,
            expires_in=settings.TOKEN_EXPIRATION_TIME,
            issued_at=_dt_now.isoformat(),
        )

        # Set user session
        request.session["user"] = dict(user)
        request.session["token"] = json.loads(jwt_token.model_dump_json())
        logger.info("User session set successfully.")  # Log session success
        return fastapi.responses.RedirectResponse(url="/")

    except Exception as e:
        logger.error(
            f"Error during Google OAuth callback: {e}", exc_info=True
        )  # Log any error with full traceback
        raise e  # Re-raise the exception so FastAPI handles it


@router.get("/auth/logout")
async def logout(request: fastapi.Request):
    request.session.pop("user", None)
    return fastapi.responses.RedirectResponse(url="/")


@router.get("/auth/protected")
async def protected_route(
    user: UserInDB = fastapi.Depends(depends_session_active_user),
):
    return {
        "message": (
            f"Hello, {user.full_name or user.username}! This is a protected route."
        )
    }
