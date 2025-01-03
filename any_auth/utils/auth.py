import base64
import secrets
import typing


def generate_jwt_secret() -> typing.Text:
    # Generate a 512-bit (64-byte) random key for enhanced security
    # Using secrets.token_bytes is more direct than token_hex for cryptographic keys
    random_bytes = secrets.token_bytes(64)

    # Convert to URL-safe base64 format to ensure compatibility with JWT
    # and remove padding characters
    secret_key = base64.urlsafe_b64encode(random_bytes).decode("utf-8").rstrip("=")
    return secret_key
