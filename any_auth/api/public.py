# any_auth/api/public.py
import asyncio
import logging

import fastapi

import any_auth.deps.app_state as AppState
from any_auth.backend import BackendClient
from any_auth.types.user import User, UserCreate

logger = logging.getLogger(__name__)

router = fastapi.APIRouter()


@router.post(
    "/public/register",
    response_model=User,
    tags=["Public"],
    status_code=fastapi.status.HTTP_201_CREATED,
)
async def public_register_user(
    user_create: UserCreate = fastapi.Body(
        ..., description="User registration details"
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    """
    Public endpoint for user self-registration.
    IMPORTANT: Add rate limiting, CAPTCHA, and email verification for production use.
    """

    logger.info(f"Attempting public registration for email: {user_create.email}")

    # 1. Check if email already exists
    existing_by_email = await asyncio.to_thread(
        backend_client.users.retrieve_by_email, user_create.email
    )
    if existing_by_email:
        logger.warning(
            f"Registration attempt failed: Email '{user_create.email}' already exists."
        )
        # Return a generic message to avoid leaking information
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_409_CONFLICT,
            detail="A user with this email or username already exists.",
        )

    # 2. Check if username already exists
    existing_by_username = await asyncio.to_thread(
        backend_client.users.retrieve_by_username, user_create.username
    )
    if existing_by_username:
        logger.warning(
            f"Registration attempt failed: Username '{user_create.username}' "
            + "already exists."
        )
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_409_CONFLICT,
            detail="A user with this email or username already exists.",
        )

    # TODO: Add More Security Here in Production
    # - CAPTCHA verification
    # - More sophisticated rate limiting

    # Create User
    try:
        # Create the user in the database
        user_in_db = await asyncio.to_thread(
            backend_client.users.create,
            user_create,
        )
        logger.info(
            f"Successfully registered user {user_in_db.username} "
            + f"({user_in_db.id}) via public endpoint."
        )

        # TODO: Trigger Email Verification Here

    except fastapi.HTTPException as e:
        raise e

    except Exception as e:
        logger.exception(e)
        logger.exception(
            f"Error during public user registration for email {user_create.email}: {e}"
        )
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during registration.",
        )

    # Return the publicly viewable User model, not UserInDB which has the hash
    return User.model_validate(user_in_db.model_dump())
