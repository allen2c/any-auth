import logging
import typing

import fastapi
from authlib.integrations.starlette_client import OAuth
from authlib.integrations.starlette_client.apps import StarletteOAuth2App

import any_auth.deps.app_state as AppState
from any_auth.backend import BackendClient
from any_auth.backend.users import UserCreate
from any_auth.config import Settings
from any_auth.types.oauth import SessionStateGoogleData, TokenUserInfo

logger = logging.getLogger(__name__)

router = fastapi.APIRouter()


def get_current_user(request: fastapi.Request):
    user = request.session.get("user")
    if not user:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    return user


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

        # Set user session
        request.session["user"] = dict(user)
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
async def protected_route(user: dict = fastapi.Depends(get_current_user)):
    return {"message": f"Hello, {user['name']}! This is a protected route."}
