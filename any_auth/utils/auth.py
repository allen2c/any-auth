import base64
import functools
import logging
import re
import secrets
import typing

import bcrypt
from fastapi.security import OAuth2PasswordBearer

from any_auth.types.role import Permission, Role
from any_auth.types.user import UserInDB

logger = logging.getLogger(__name__)


@functools.lru_cache
def get_oauth2_scheme(
    tokenUrl: typing.Text = "token",
    scheme_name: typing.Text | None = None,
    scopes: typing.Dict[typing.Text, typing.Text] | None = None,
    description: typing.Text | None = None,
    auto_error: bool = True,
) -> OAuth2PasswordBearer:
    return OAuth2PasswordBearer(
        tokenUrl=tokenUrl,
        scheme_name=scheme_name,
        scopes=scopes,
        description=description,
        auto_error=auto_error,
    )


def generate_jwt_secret() -> typing.Text:
    # Generate a 512-bit (64-byte) random key for enhanced security
    # Using secrets.token_bytes is more direct than token_hex for cryptographic keys
    random_bytes = secrets.token_bytes(64)

    # Convert to URL-safe base64 format to ensure compatibility with JWT
    # and remove padding characters
    secret_key = base64.urlsafe_b64encode(random_bytes).decode("utf-8").rstrip("=")
    return secret_key


def hash_password(password: typing.Text) -> typing.Text:
    # Generate a salt
    salt = bcrypt.gensalt()
    # Hash the password
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), salt)
    # Return the hashed password as a string
    return hashed_password.decode("utf-8")


def verify_password(password: typing.Text, hashed_password: typing.Text) -> bool:
    # Check if the password matches the hashed password
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


password_pattern = re.compile(
    r"^"  # Start of the string
    r"(?=.*[A-Z])"  # Positive lookahead for at least one uppercase letter
    r"(?=.*[a-z])"  # Positive lookahead for at least one lowercase letter
    r"(?=.*\d)"  # Positive lookahead for at least one digit
    r'(?=.*[!"#$%&\'()*+,\-./:;<=>?@\[\\\]^_`{|}~])'  # Positive lookahead for at least one special character  # noqa: E501
    r'[A-Za-z\d!"#$%&\'()*+,\-./:;<=>?@$begin:math:display$\\\\$end:math:display$^_`{|}~]{8,64}'  # Allowed characters and length between 8 and 64  # noqa: E501
    r"$"  # End of the string
)


def is_valid_password(password: typing.Text) -> bool:
    return bool(password_pattern.match(password))


def raise_if_not_enough_permissions(
    required_permissions: typing.Iterable[Permission],
    user_permissions: typing.Iterable[Permission],
    *,
    debug_active_user: UserInDB | None = None,
    debug_user_roles: typing.Iterable[Role] | None = None,
    debug_resource_id: str | None = None,
    debug_resource_type: (
        typing.Literal["organization", "project", "platform"] | None
    ) = None,
) -> None:
    """Check if user is missing anything"""

    import fastapi

    import any_auth.utils.to_ as TO

    missing = set(required_permissions) - set(user_permissions)

    if missing:
        # missing permissions
        _missing_exprs = [f"'{str(TO.to_enum_value(perm))}'" for perm in missing]
        missing_str = ", ".join(_missing_exprs)

        # required permissions
        _needed_exprs = [
            f"'{str(TO.to_enum_value(perm))}'" for perm in required_permissions
        ]
        needed_str = ", ".join(_needed_exprs)

        # user roles
        user_roles_str: typing.Text | None = None
        if debug_user_roles is not None:
            _user_roles_exprs = [
                f"'{str(TO.to_enum_value(role.name))}'" for role in debug_user_roles
            ]
            user_roles_str = ", ".join(_user_roles_exprs)

        # user permissions
        user_perms_str: typing.Text | None = None
        if user_permissions is not None:
            _user_perms_exprs = [
                f"'{str(TO.to_enum_value(perm))}'" for perm in user_permissions
            ]
            user_perms_str = ", ".join(_user_perms_exprs)

        # warn message
        warn_msg = ""
        if debug_active_user is None:
            warn_msg += "Permission verification failed: "
        else:
            warn_msg += f"Insufficient permissions for user '{debug_active_user.id}', "
        if debug_user_roles is not None:
            warn_msg += f"Roles: [{user_roles_str}], "
        warn_msg += f"Current Permissions: [{user_perms_str}], "
        warn_msg += f"Missing Permissions: [{missing_str}], "
        warn_msg += f"Required Permissions: [{needed_str}], "
        warn_msg += (
            f"Resource: {debug_resource_type or 'NotProvidedForDebugging'}, "
            f"ID: {debug_resource_id or 'NotProvidedForDebugging'}"
        )

        logger.warning(warn_msg)

        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    return None
