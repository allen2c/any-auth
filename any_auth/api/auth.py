import logging
import typing

import fastapi
from authlib.integrations.starlette_client import OAuth
from authlib.integrations.starlette_client.apps import StarletteOAuth2App

logger = logging.getLogger(__name__)

router = fastapi.APIRouter()


async def depends_oauth(request: fastapi.Request) -> OAuth:
    return request.app.state.oauth


def get_current_user(request: fastapi.Request):
    user = request.session.get("user")
    if not user:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    return user


@router.get("/auth")
async def homepage(request: fastapi.Request):
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
    request: fastapi.Request, oauth: OAuth = fastapi.Depends(depends_oauth)
):
    redirect_uri = request.url_for("auth")
    oauth_google = typing.cast(StarletteOAuth2App, oauth.google)
    return await oauth_google.authorize_redirect(request, redirect_uri)


@router.get("/auth/google/callback")
async def auth(request: fastapi.Request, oauth: OAuth = fastapi.Depends(depends_oauth)):
    logger.info("--- Google Callback Started ---")  # Log start of callback
    logger.info(f"Request URL: {request.url}")  # Log the full request URL
    logger.info(f"Request Session: {request.session}")  # Log session data

    try:
        oauth_google = typing.cast(StarletteOAuth2App, oauth.google)
        token = await oauth_google.authorize_access_token(request)
        logger.info(f"Token received: {token}")  # Log the token object
        logger.info(f"Token type: {type(token)}")  # Log the type of 'token'
        logger.info(
            f"Token keys: {token.keys() if hasattr(token, 'keys') else 'No keys() method'}"
        )  # Log keys if it's a dict-like object
        logger.info(
            f"Does 'id_token' exist in token? {'id_token' in token}"
        )  # Explicit check
        logger.warning(type(oauth.google))
        user = await oauth_google.parse_id_token(token)
        logger.info(f"User parsed from ID Token: {user}")  # Log user info
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
