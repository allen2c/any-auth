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

    # JWT
    JWT_SECRET_KEY: pydantic.SecretStr = pydantic.Field(...)
    JWT_ALGORITHM: typing.Literal["HS256"] = pydantic.Field(default="HS256")
