import logging
import textwrap
import time

import fastapi
import jwt

import any_auth.deps.app_state as AppState
import any_auth.utils.is_ as IS
import any_auth.utils.jwt_manager as JWTManager
from any_auth.backend import BackendClient
from any_auth.config import Settings
from any_auth.types.token import Token
from any_auth.types.user import UserInDB
from any_auth.utils.auth import verify_password

logger = logging.getLogger(__name__)

router = fastapi.APIRouter()


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


@router.get("/c/welcome", tags=["Console"])
async def auth_console(request: fastapi.Request):
    user = request.session.get("user")
    if user:
        return fastapi.responses.HTMLResponse(
            f"""
            <h1>Hello, {user['name']}!</h1>
            <img src="{user['picture']}">
            <p><a href="/c/user">User Profile</a></p>
            <p><a href="/c/logout">Logout</a></p>
        """
        )
    else:
        return fastapi.responses.RedirectResponse(url="/c/login")


@router.get("/c/login", tags=["Console"])
async def auth_console_login(request: fastapi.Request):
    """
    If user is already in session, redirect them to /c/welcome.
    Otherwise, show a simple HTML form for username/email and password.
    """

    user = request.session.get("user")
    if user:
        return fastapi.responses.RedirectResponse(url="/c/welcome")

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
                <form action="/c/login" method="post">
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
                <a href="/c/google/login">Login with Google</a>
            </body>
        </html>
        """  # noqa: E501
    )
    return fastapi.responses.HTMLResponse(content=html_form)


@router.post("/c/login", tags=["Console"])
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

    # 6. Redirect to the main /c/welcome route (or wherever you like)
    return fastapi.responses.RedirectResponse(url="/c/welcome", status_code=302)


@router.get("/c/user", tags=["Console"])
async def protected_route(
    user: UserInDB = fastapi.Depends(depends_console_session_active_user),
):
    return {
        "message": (
            f"Hello, {user.full_name or user.username}! This is a protected route."
        )
    }


@router.get("/c/logout", tags=["Console"])
async def auth_console_logout(request: fastapi.Request):
    request.session.clear()
    return fastapi.responses.RedirectResponse(url="/c/login")


@router.get("/c/expired", tags=["Console"])
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
