import base64
import functools
import re
import secrets
import typing

import bcrypt
from fastapi.security import OAuth2PasswordBearer


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
