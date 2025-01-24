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
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

import any_auth.deps.app_state as AppState
import any_auth.utils.is_ as IS
import any_auth.utils.jwt_manager as JWTManager
from any_auth.backend import BackendClient
from any_auth.backend.users import UserCreate
from any_auth.config import Settings
from any_auth.types.oauth import SessionStateGoogleData, TokenUserInfo
from any_auth.types.token import Token
from any_auth.types.user import UserInDB
from any_auth.utils.auth import verify_password

logger = logging.getLogger(__name__)

router = fastapi.APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def depends_current_user(
    token: typing.Annotated[str, fastapi.Depends(oauth2_scheme)],
    settings: Settings = fastapi.Depends(AppState.depends_settings),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> UserInDB:
    try:
        payload = JWTManager.verify_jwt_token(
            token,
            jwt_secret=settings.JWT_SECRET_KEY.get_secret_value(),
            jwt_algorithm=settings.JWT_ALGORITHM,
        )
        user_id = JWTManager.get_user_id_from_payload(payload)

        if time.time() > payload["exp"]:
            raise jwt.ExpiredSignatureError

    except jwt.ExpiredSignatureError:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.InvalidTokenError:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    except Exception as e:
        logger.exception(e)
        logger.error("Error during session active user")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

    if not user_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    user_in_db = backend_client.users.retrieve(user_id)

    if not user_in_db:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user_in_db


async def depends_active_user(
    user: UserInDB = fastapi.Depends(depends_current_user),
) -> UserInDB:
    if user.disabled:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="User is not active",
        )
    return user


async def depends_console_session_active_user(
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


@router.get("/token")
async def auth_token(
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
        user_in_db = backend_client.users.retrieve_by_email(form_data.username)
    else:
        user_in_db = backend_client.users.retrieve_by_username(form_data.username)

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


@router.get("/logout")
async def auth_logout(request: fastapi.Request):
    raise fastapi.HTTPException(
        status_code=fastapi.status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented"
    )


@router.get("/refresh-token")
async def auth_refresh_token(request: fastapi.Request):
    raise fastapi.HTTPException(
        status_code=fastapi.status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented"
    )


@router.get("/auth", tags=["Console"])
async def auth_console(request: fastapi.Request):
    user = request.session.get("user")
    if user:
        return fastapi.responses.HTMLResponse(
            f"""
            <h1>Hello, {user['name']}!</h1>
            <img src="{user['picture']}">
            <p><a href="/auth/user">User Profile</a></p>
            <p><a href="/auth/logout">Logout</a></p>
        """
        )
    else:
        return fastapi.responses.RedirectResponse(url="/auth/login")


@router.get("/auth/login", tags=["Console"])
async def auth_console_login(request: fastapi.Request):
    """
    If user is already in session, redirect them to /auth.
    Otherwise, show a simple HTML form for username/email and password.
    """

    user = request.session.get("user")
    if user:
        return fastapi.responses.RedirectResponse(url="/auth")

    # Provide a simple HTML form
    # You can style or template this any way you'd like
    html_form = textwrap.dedent(
        """
        <!DOCTYPE html>
        <html>
            <head>
            <title>Login</title>
            </head>
            <body>
                <h1>Login</h1>
                <form action="/auth/login" method="post">
                <div>
                    <label for="username_or_email">Username or Email</label>
                    <input type="text" id="username_or_email" name="username_or_email" required />
                </div>
                <div>
                    <label for="password">Password</label>
                    <input type="password" id="password" name="password" required />
                </div>
                <button type="submit">Login</button>
                </form>
                <hr />
                <h3>Or Login With Google</h3>
                <a href="/auth/google/login">Login with Google</a>
            </body>
        </html>
        """  # noqa: E501
    )
    return fastapi.responses.HTMLResponse(content=html_form)


@router.post("/auth/login", tags=["Console"])
async def post_auth_console_login(
    request: fastapi.Request,
    username_or_email: str = fastapi.Form(...),
    password: str = fastapi.Form(...),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
    settings: Settings = fastapi.Depends(AppState.depends_settings),
):
    """
    Handle form submission from the login page. Check credentials.
    If valid, create a session and store a JWT token; otherwise, raise HTTP 401.
    """

    username_or_email = username_or_email.strip()
    is_email = IS.is_email(username_or_email)

    # 1. Retrieve user by username or email
    if is_email:
        user_in_db = backend_client.users.retrieve_by_email(username_or_email)
    else:
        user_in_db = backend_client.users.retrieve_by_username(username_or_email)

    if not user_in_db:
        # User does not exist
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password",
        )

    # 2. Verify password
    if not verify_password(password, user_in_db.hashed_password):
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password",
        )

    # 3. Generate JWT tokens
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

    # 4. Build a Token object
    token = Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        scope="openid email profile",
        expires_in=settings.TOKEN_EXPIRATION_TIME,
        expires_at=now_ts + settings.TOKEN_EXPIRATION_TIME,
    )

    # 5. Store relevant info in session
    request.session["user"] = {
        "id": user_in_db.id,
        "email": user_in_db.email,
        "name": user_in_db.full_name or user_in_db.username,
        "picture": user_in_db.picture,  # or None
    }
    # Convert the `Token` pydantic model to a dict for session storage
    request.session["token"] = token.model_dump(mode="json")

    # 6. Redirect to the main /auth route (or wherever you like)
    return fastapi.responses.RedirectResponse(url="/auth", status_code=302)


@router.get("/auth/user", tags=["Console"])
async def protected_route(
    user: UserInDB = fastapi.Depends(depends_console_session_active_user),
):
    return {
        "message": (
            f"Hello, {user.full_name or user.username}! This is a protected route."
        )
    }


@router.get("/auth/logout", tags=["Console"])
async def auth_console_logout(request: fastapi.Request):
    request.session.clear()
    return fastapi.responses.RedirectResponse(url="/auth/login")


@router.get("/auth/expired", tags=["Console"])
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


@router.get("/auth/google/login", tags=["Console"])
async def login(
    request: fastapi.Request, oauth: OAuth = fastapi.Depends(AppState.depends_oauth)
):
    redirect_uri = request.url_for("auth")
    oauth_google = typing.cast(StarletteOAuth2App, oauth.google)
    return await oauth_google.authorize_redirect(request, redirect_uri)


@router.get("/auth/google/callback", tags=["Console"])
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
        return fastapi.responses.RedirectResponse(url="/auth")

    except Exception as e:
        logger.error(
            f"Error during Google OAuth callback: {e}", exc_info=True
        )  # Log any error with full traceback
        raise e  # Re-raise the exception so FastAPI handles it
