import base64
import functools
import secrets
import typing

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
