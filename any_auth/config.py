import logging
import os
import re
import typing

import faker
import pydantic
from pydantic_settings import BaseSettings

from any_auth.logger_name import LOGGER_NAME

logger = logging.getLogger(LOGGER_NAME)


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

    # Class Vars
    fake: typing.ClassVar[faker.Faker] = faker.Faker()

    @classmethod
    def required_environment_variables(cls):
        return (
            "DATABASE_URL",
            "JWT_SECRET_KEY",
        )

    @classmethod
    def probe_required_environment_variables(cls) -> None:
        for env_var in cls.required_environment_variables():
            if os.getenv(env_var) is not None:
                continue
            # Try to match the env var name in case insensitive manner
            for env_var_candidate in os.environ.keys():
                if re.match(env_var, env_var_candidate, re.IGNORECASE):
                    continue
            logger.warning(f"Environment variable {env_var} is not set")

        return None
