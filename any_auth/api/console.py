"""
This frontend design style is characterized by a **clean, modern, and highly functional aesthetic.** It prioritizes clarity and usability, especially for complex data and workflows.

**Color Palette:**

* **Dominantly Light and Neutral Backgrounds:**  The interface primarily uses white and very light grays as background colors. This creates a sense of spaciousness and cleanliness, improving readability and reducing visual clutter.
* **Accent Colors Based on a Primary Brand Hue:** A corporate brand color, often in the blue family, is used as the main accent. This color is strategically applied to interactive elements like buttons, links, and key navigation items to draw attention and indicate actions.
* **Status-Indicating Colors:**  Colors like green, red, and orange are consistently used to convey status and importance. Green typically signifies success or healthy states, red indicates errors or critical issues, and orange/yellow flags warnings or potential problems.
* **Neutral Grays for Text and Secondary Elements:**  Various shades of gray are used for text, icons, and less prominent UI elements. Darker grays ensure text readability, while lighter grays provide subtle visual separation without being distracting.

**Design Style:**

* **Modern and Flat Design Principles:**  The style embraces flat design, minimizing gradients and ornamentation. It emphasizes clean lines, geometric shapes, and a streamlined appearance for a contemporary feel.
* **Focus on Functionality and Data Presentation:** The primary design goal is to present information and facilitate tasks efficiently. Design choices are driven by usability and the need to handle large amounts of data clearly and understandably.
* **Consistent and Structured Layout:**  The interface maintains a consistent layout across different sections, making navigation intuitive and predictable. Information is often organized into structured panels, tables, and forms for clarity.
* **Minimalist and Uncluttered Approach:**  The design avoids unnecessary visual elements and distractions.  It focuses on essential information and controls, promoting a focused and efficient user experience.
* **Professional and Business-Oriented Feel:** The overall style is professional and serious, suitable for business and enterprise applications. It avoids playful or overly decorative elements, projecting an image of reliability and competence.
* **Subtle Use of Depth:** While primarily flat, subtle shadows or layering might be used sparingly to create visual hierarchy and separate elements, adding a touch of depth without compromising the clean aesthetic.
* **Emphasis on Clear Typography:**  Legible and well-chosen typography is a key element, ensuring readability and a professional look, particularly important for data-rich interfaces.

**In Summary:**

This design style can be generally described as **clean, modern, functional, and professional.** It leverages a light and neutral color palette accented by a brand color and status indicators, applying flat design principles and a minimalist approach to prioritize usability, data clarity, and a business-oriented user experience.  It's a style commonly seen in platforms designed for complex tasks, data management, and professional users.
"""  # noqa: E501

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
async def web_welcome(request: fastapi.Request):
    user = request.session.get("user")
    if user:
        return fastapi.responses.HTMLResponse(
            f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Welcome, {user['name']}!</title>
                <style>
                    body {{
                        font-family: 'Arial', sans-serif;
                        background-color: #f4f4f4;
                        margin: 0;
                        padding: 0;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        min-height: 100vh;
                    }}
                    .container {{
                        background-color: #fff;
                        padding: 30px;
                        border-radius: 8px;
                        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                        text-align: center;
                        width: 80%;
                        max-width: 600px;
                    }}
                    h1 {{
                        color: #333;
                        margin-bottom: 20px;
                    }}
                    img {{
                        width: 100px;
                        height: 100px;
                        border-radius: 50%;
                        margin-bottom: 20px;
                        border: 3px solid #ddd;
                    }}
                    .links {{
                        margin-top: 30px;
                    }}
                    .link-btn {{
                        display: inline-block;
                        padding: 10px 20px;
                        margin: 0 10px;
                        background-color: #007bff;
                        color: white;
                        text-decoration: none;
                        border-radius: 5px;
                        transition: background-color 0.3s ease;
                    }}
                    .link-btn:hover {{
                        background-color: #0056b3;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Welcome, {user['name']}!</h1>
                    <img src="{user['picture']}" alt="User Profile Picture">
                    <div class="links">
                        <a href="/c/user" class="link-btn">User Profile</a>
                        <a href="/c/logout" class="link-btn">Logout</a>
                    </div>
                </div>
            </body>
            </html>
            """
        )
    else:
        return fastapi.responses.RedirectResponse(url="/c/login")


@router.get("/c/login", tags=["Console"])
async def web_login(request: fastapi.Request):
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
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {
                    font-family: 'Arial', sans-serif;
                    background-color: #f4f4f4;
                    margin: 0;
                    padding: 0;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                }
                .container {
                    background-color: #fff;
                    padding: 40px;
                    border-radius: 8px;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    width: 80%;
                    max-width: 500px;
                    text-align: center;
                }
                h1 {
                    color: #333;
                    margin-bottom: 30px;
                }
                input[type="text"],
                input[type="password"] {
                    width: 100%;
                    padding: 12px;
                    margin: 10px 0;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    box-sizing: border-box;
                }
                button[type="submit"],
                .google-login-btn {
                    background-color: #007bff;
                    color: white;
                    border: none;
                    padding: 12px 20px;
                    border-radius: 5px;
                    cursor: pointer;
                    transition: background-color 0.3s ease;
                    font-size: 16px;
                    margin-top: 20px;
                    text-decoration: none;
                    display: inline-block;
                    width: 100%; /* Make buttons full width */
                    box-sizing: border-box; /* Ensure padding and border are included in the width */
                }
                button[type="submit"]:hover,
                .google-login-btn:hover {
                    background-color: #0056b3;
                }
                .google-login-btn {
                    background-color: #db4437; /* Google Red Color */
                }
                .google-login-btn:hover {
                    background-color: #c5382b;
                }
                hr {
                    margin-top: 30px;
                    margin-bottom: 30px;
                    border: 0;
                    border-top: 1px solid #eee;
                }
            </style>
            </head>
            <body>
                <div class="container">
                <h1>Login</h1>
                <form action="/c/login" method="post">
                    <input type="text" id="username_or_email" name="username_or_email" placeholder="Username or Email" required />
                    <input type="password" id="password" name="password" placeholder="Password" required />
                    <button type="submit">Login</button>
                </form>
                <hr />
                <div>
                    <h3>Or Login With Google</h3>
                    <a href="/auth/google/login" class="google-login-btn">Login with Google</a>
                </div>
                </div>
            </body>
        </html>
        """  # noqa: E501
    )
    return fastapi.responses.HTMLResponse(content=html_form)


@router.post("/c/login", tags=["Console"])
async def post_web_login(
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
async def web_user_profile(
    user: UserInDB = fastapi.Depends(depends_console_session_active_user),
):
    """
    Display the user profile page.
    """
    return fastapi.responses.HTMLResponse(
        f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>User Profile - AnyAuth Console</title>
            <style>
                body {{
                    font-family: 'Arial', sans-serif;
                    background-color: #f4f4f4;
                    margin: 0;
                    padding: 0;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                }}
                .container {{
                    background-color: #fff;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    width: 80%;
                    max-width: 600px;
                    text-align: center;
                }}
                h1 {{
                    color: #333;
                    margin-bottom: 20px;
                }}
                img {{
                    width: 100px;
                    height: 100px;
                    border-radius: 50%;
                    margin-bottom: 20px;
                    border: 3px solid #ddd;
                }}
                .profile-info {{
                    text-align: left;
                    margin-bottom: 20px;
                }}
                .profile-info p {{
                    margin: 10px 0;
                    color: #555;
                }}
                .links {{
                    margin-top: 30px;
                }}
                .link-btn {{
                    display: inline-block;
                    padding: 10px 20px;
                    margin: 0 10px;
                    background-color: #007bff;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    transition: background-color 0.3s ease;
                }}
                .link-btn:hover {{
                    background-color: #0056b3;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Your Profile</h1>
                <img src="{user.picture}" alt="User Profile Picture">
                <div class="profile-info">
                    <p><strong>Username:</strong> {user.username}</p>
                    <p><strong>Full Name:</strong> {user.full_name or 'N/A'}</p>
                    <p><strong>Email:</strong> {user.email}</p>
                </div>
                <div class="links">
                    <a href="/c/welcome" class="link-btn">Dashboard</a>
                    <a href="/c/logout" class="link-btn">Logout</a>
                </div>
            </div>
        </body>
        </html>
        """
    )


@router.get("/c/logout", tags=["Console"])
async def web_logout(request: fastapi.Request):
    request.session.clear()
    return fastapi.responses.RedirectResponse(url="/c/login")


@router.get("/c/expired", tags=["Console"])
async def web_expired():
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
                    <a href="/c/login" class="login-btn">Login with Google</a>
                </div>
            </body>
            </html>
            """
        ),
        status_code=fastapi.status.HTTP_410_GONE,
    )
