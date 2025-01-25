import asyncio
import datetime
import json
import logging
import secrets
import time
import typing
import zoneinfo

import diskcache
import fastapi
import fastapi_mail
import redis
from authlib.integrations.starlette_client import OAuth
from authlib.integrations.starlette_client.apps import StarletteOAuth2App
from fastapi.security import OAuth2PasswordRequestForm

import any_auth.deps.app_state as AppState
import any_auth.utils.is_ as IS
import any_auth.utils.jwt_manager as JWTManager
from any_auth.backend import BackendClient
from any_auth.backend.users import UserCreate
from any_auth.config import Settings
from any_auth.deps.auth import depends_active_user, oauth2_scheme
from any_auth.types.oauth import SessionStateGoogleData, TokenUserInfo
from any_auth.types.token import Token
from any_auth.types.user import User, UserInDB
from any_auth.utils.auth import verify_password

logger = logging.getLogger(__name__)

router = fastapi.APIRouter()


@router.post("/token")
async def api_token(
    form_data: typing.Annotated[OAuth2PasswordRequestForm, fastapi.Depends()],
    settings: Settings = fastapi.Depends(AppState.depends_settings),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Token:
    if not form_data.username or not form_data.password:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Missing username or password",
        )

    is_email = IS.is_email(form_data.username)
    if is_email:
        user_in_db = await asyncio.to_thread(
            backend_client.users.retrieve_by_email, form_data.username
        )
    else:
        user_in_db = await asyncio.to_thread(
            backend_client.users.retrieve_by_username, form_data.username
        )

    if not user_in_db:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password",
        )

    if not verify_password(form_data.password, user_in_db.hashed_password):
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password",
        )

    now_ts = int(time.time())
    access_token = JWTManager.create_jwt_token(
        user_id=user_in_db.id,
        expires_in=settings.TOKEN_EXPIRATION_TIME,
        jwt_secret=settings.JWT_SECRET_KEY.get_secret_value(),
        jwt_algorithm=settings.JWT_ALGORITHM,
        now=now_ts,
    )
    refresh_token = JWTManager.create_jwt_token(
        user_id=user_in_db.id,
        expires_in=settings.REFRESH_TOKEN_EXPIRATION_TIME,
        jwt_secret=settings.JWT_SECRET_KEY.get_secret_value(),
        jwt_algorithm=settings.JWT_ALGORITHM,
        now=now_ts,
    )

    # Build a Token object
    token = Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        scope="openid email profile",
        expires_in=settings.TOKEN_EXPIRATION_TIME,
        expires_at=now_ts + settings.TOKEN_EXPIRATION_TIME,
    )
    return token


@router.post("/logout")
async def api_logout(
    request: fastapi.Request,
    token: Token = fastapi.Depends(oauth2_scheme),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    cache: diskcache.Cache | redis.Redis = fastapi.Depends(AppState.depends_cache),
    settings: Settings = fastapi.Depends(AppState.depends_settings),
):
    # Add blacklist token
    cache.set(
        f"token_blacklist:{token.access_token}",
        True,
        settings.TOKEN_EXPIRATION_TIME + 1,
    )
    return fastapi.responses.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)


@router.post("/refresh-token")
async def api_refresh_token(
    request: fastapi.Request,
    token: typing.Text = fastapi.Depends(oauth2_scheme),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    cache: diskcache.Cache | redis.Redis = fastapi.Depends(AppState.depends_cache),
    settings: Settings = fastapi.Depends(AppState.depends_settings),
) -> Token:
    # Add blacklist token
    cache.set(
        f"token_blacklist:{token}",
        True,
        settings.REFRESH_TOKEN_EXPIRATION_TIME + 1,
    )

    # Generate new access token
    now_ts = int(time.time())
    access_token = JWTManager.create_jwt_token(
        user_id=active_user.id,
        expires_in=settings.TOKEN_EXPIRATION_TIME,
        jwt_secret=settings.JWT_SECRET_KEY.get_secret_value(),
        jwt_algorithm=settings.JWT_ALGORITHM,
        now=now_ts,
    )
    refresh_token = JWTManager.create_jwt_token(
        user_id=active_user.id,
        expires_in=settings.REFRESH_TOKEN_EXPIRATION_TIME,
        jwt_secret=settings.JWT_SECRET_KEY.get_secret_value(),
        jwt_algorithm=settings.JWT_ALGORITHM,
        now=now_ts,
    )
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        scope="openid email profile",
        expires_in=settings.TOKEN_EXPIRATION_TIME,
        expires_at=now_ts + settings.TOKEN_EXPIRATION_TIME,
    )


@router.post("/reset-password")
async def api_reset_password(
    request: fastapi.Request,
    token: typing.Text = fastapi.Query(...),
    form_data: OAuth2PasswordRequestForm = fastapi.Depends(),
    cache: diskcache.Cache | redis.Redis = fastapi.Depends(AppState.depends_cache),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    if not token:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Missing token",
        )

    user_id = cache.get(f"reset_password:{token}")
    if not user_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    user_id = typing.cast(typing.Text, user_id)

    new_password = form_data.password

    if not new_password:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Missing new password",
        )

    await asyncio.to_thread(backend_client.users.reset_password, user_id, new_password)

    return fastapi.responses.JSONResponse(
        status_code=fastapi.status.HTTP_200_OK,
        content={"detail": "Password reset successfully"},
    )


@router.post("/request-reset-password")
async def api_request_reset_password(
    request: fastapi.Request,
    email: str,  # For security, often you'd make this a POST body param
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
    smtp_mailer: fastapi_mail.FastMail = fastapi.Depends(AppState.depends_smtp_mailer),
    settings: Settings = fastapi.Depends(AppState.depends_settings),
    cache: diskcache.Cache | redis.Redis = fastapi.Depends(AppState.depends_cache),
) -> fastapi.responses.JSONResponse:
    """
    Begin the password-reset flow by emailing the user a reset link.
    """

    # 1. Attempt to find user by email
    user = await asyncio.to_thread(backend_client.users.retrieve_by_email, email)

    # 2. Generate a reset token (random string or a short-lived JWT)
    reset_token = secrets.token_urlsafe(32)  # random 32-byte token

    # 3. If user found, store the token -> user mapping in your cache/DB
    #    (Setting a short expiration, e.g. 15 minutes = 900 seconds)
    if user:
        cache_key = f"reset_password:{reset_token}"
        # The cached value could be as simple as just the user ID
        cache.set(cache_key, user.id, 900)

    # 4. Compose the reset URL you want the user to click
    #    For example, a front-end page: e.g. https://myapp.com/reset?token=XYZ
    #    Or an API endpoint that does the final reset.
    reset_url = f"http://localhost:8000/c/reset-password?token={reset_token}"

    # 5. Send the email. If you’re using fastapi-mail:
    subject = "Your Password Reset Request"
    recipients = [email]  # list of recipients
    body = (
        f"Hello,\n\n"
        f"If you requested a password reset, click the link below:\n\n"
        f"{reset_url}\n\n"
        "If you did NOT request this, you can safely ignore this email."
    )

    # Even if the user doesn't exist, you can still "pretend" to send.
    # That way you don't leak which emails are in your system.
    message = fastapi_mail.MessageSchema(
        subject=subject,
        recipients=recipients,  # List of email strings
        body=body,
        subtype=fastapi_mail.MessageType.plain,
    )

    try:
        await smtp_mailer.send_message(message)
    except Exception as e:
        logger.exception(e)
        # Log the error, possibly return a 500.
        # For security, do NOT reveal email-sending errors to the client.
        # Instead you might just log and claim success anyway:
        logger.error(f"Email send error: {e}")

    # 6. Always respond with success to avoid revealing that an account does/doesn’t exist  # noqa: E501
    return fastapi.responses.JSONResponse(
        status_code=fastapi.status.HTTP_200_OK,
        content={"detail": "If a user with that email exists, a reset link was sent."},
    )


@router.get("/me")
async def api_me(active_user: UserInDB = fastapi.Depends(depends_active_user)) -> User:
    return active_user


@router.get("/auth/google/login", tags=["OAuth"])
async def api_google_login(
    request: fastapi.Request,
    redirect_url: typing.Text = fastapi.Query(default=""),
    oauth: OAuth = fastapi.Depends(AppState.depends_oauth),
):
    redirect_url = redirect_url.strip()

    redirect_uri = request.url_for("api_google_callback")
    oauth_google = typing.cast(StarletteOAuth2App, oauth.google)

    state_payload = {"redirect_url": "/c/welcome"}
    whitelist_redirect_url = [
        "/c",
        "/c/welcome",
        "/c/user",
        "/c/logout",
    ]
    if redirect_url:
        if redirect_url in whitelist_redirect_url:
            logger.debug(f"Redirect URL: {redirect_url}")
            state_payload["redirect_url"] = redirect_url
        else:
            logger.warning(f"Redirect URL: {redirect_url} is not in whitelist")

    return await oauth_google.authorize_redirect(
        request,
        redirect_uri,
        scope="openid email profile",
        state=json.dumps(state_payload),
    )


@router.get("/auth/google/callback", tags=["OAuth"])
async def api_google_callback(
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

        # Get state from query params
        state_str = request.query_params.get("state")
        if state_str:
            state_payload = json.loads(state_str)
            final_redirect_url = state_payload.get("redirect_url", "/c/welcome")
        else:
            final_redirect_url = "/c/welcome"

        user = await oauth_google.parse_id_token(
            token, nonce=session_state_google.data["nonce"]
        )
        user_info = TokenUserInfo.model_validate(user)
        logger.info(f"User parsed from ID Token: {user}")  # Log user info

        # Create user if not exists
        user_info.raise_if_not_name()
        user_info.raise_if_not_email()
        user_in_db = await asyncio.to_thread(
            backend_client.users.retrieve_by_email, user_info.email
        )
        if not user_in_db:
            _username = f"usr_{secrets.token_urlsafe(32)}"
            user_in_db = await asyncio.to_thread(
                backend_client.users.create,
                UserCreate(
                    username=_username,
                    full_name=user_info.given_name or user_info.name,
                    email=user_info.email,
                    phone=user_info.phone_number or None,
                    password=Settings.fake.password(),
                ),
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

        return fastapi.responses.RedirectResponse(url=final_redirect_url)

    except Exception as e:
        logger.error(
            f"Error during Google OAuth callback: {e}", exc_info=True
        )  # Log any error with full traceback
        raise e  # Re-raise the exception so FastAPI handles it
