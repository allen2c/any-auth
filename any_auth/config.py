import typing

import pydantic
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: typing.Literal["development", "production", "test"] = pydantic.Field(
        default="development",
    )

    # Database
    DATABASE_URL: pydantic.SecretStr = pydantic.Field(...)
    CACHE_URL: pydantic.SecretStr | None = pydantic.Field(default=None)

    # JWT
    JWT_SECRET_KEY: pydantic.SecretStr = pydantic.Field(...)
    JWT_ALGORITHM: typing.Literal["HS256"] = pydantic.Field(default="HS256")

    # Token Expiration
    TOKEN_EXPIRATION_TIME: int = pydantic.Field(
        default=15 * 60
    )  # 15 minutes in seconds
    REFRESH_TOKEN_EXPIRATION_TIME: int = pydantic.Field(
        default=7 * 24 * 60 * 60
    )  # 7 days in seconds
