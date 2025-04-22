import logging
import pathlib
import typing

import diskcache
import faker
import httpx
import pydantic
import redis
import redis.exceptions
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: typing.Literal["development", "production", "test"] = pydantic.Field(
        default="development",
    )

    # Database
    DATABASE_URL: pydantic.SecretStr = pydantic.Field(
        default=pydantic.SecretStr("mongodb://localhost:27017")
    )
    CACHE_URL: pydantic.SecretStr = pydantic.Field(
        default=pydantic.SecretStr("redis://localhost:6379/0")
    )
    CACHE_TTL: int = pydantic.Field(
        default=15 * 60,
        description="Default cache TTL in seconds",
    )

    # JWT
    # Choose a method to load the key (path or direct content)
    JWT_PRIVATE_KEY_PATH: pydantic.FilePath | None = pydantic.Field(default=None)
    JWT_PUBLIC_KEY_PATH: pydantic.FilePath | None = pydantic.Field(default=None)
    JWT_PRIVATE_KEY: pydantic.SecretStr | None = pydantic.Field(
        default=None, description="Private key content"
    )
    JWT_PUBLIC_KEY: pydantic.SecretStr | None = pydantic.Field(
        default=None, description="Public key content"
    )
    JWT_ALGORITHM: typing.Literal["HS256", "RS256", "ES256"] = pydantic.Field(
        default="RS256"
    )
    # (Optional) Add Key ID (kid) for key rotation
    JWT_KID: str | None = pydantic.Field(default="default-key-id")

    # Token Expiration
    TOKEN_EXPIRATION_TIME: int = pydantic.Field(
        default=15 * 60
    )  # 15 minutes in seconds
    REFRESH_TOKEN_EXPIRATION_TIME: int = pydantic.Field(
        default=7 * 24 * 60 * 60
    )  # 7 days in seconds

    # Google OAuth
    GOOGLE_CLIENT_ID: pydantic.SecretStr | None = pydantic.Field(default=None)
    GOOGLE_CLIENT_SECRET: pydantic.SecretStr | None = pydantic.Field(default=None)
    GOOGLE_REDIRECT_URI: pydantic.SecretStr | None = pydantic.Field(default=None)

    # SMTP
    SMTP_USERNAME: pydantic.SecretStr | None = pydantic.Field(default=None)
    SMTP_PASSWORD: pydantic.SecretStr | None = pydantic.Field(default=None)
    SMTP_FROM: pydantic.SecretStr | None = pydantic.Field(default=None)
    SMTP_PORT: int = pydantic.Field(default=587)
    SMTP_SERVER: pydantic.SecretStr | None = pydantic.Field(default=None)
    SMTP_STARTTLS: bool = pydantic.Field(default=True)
    SMTP_SSL_TLS: bool = pydantic.Field(default=False)
    SMTP_USE_CREDENTIALS: bool = pydantic.Field(default=True)

    # Class Vars
    fake: typing.ClassVar[faker.Faker] = faker.Faker()

    # Private
    _cache: diskcache.Cache | redis.Redis | None = None
    _local_cache: diskcache.Cache | None = None
    _private_key_content: pydantic.SecretStr | None = pydantic.PrivateAttr(default=None)
    _public_key_content: pydantic.SecretStr | None = pydantic.PrivateAttr(default=None)

    @property
    def private_key(self) -> pydantic.SecretStr:
        """Loads the private key content from path or direct config."""
        if self._private_key_content is None:
            if self.JWT_PRIVATE_KEY:
                self._private_key_content = self.JWT_PRIVATE_KEY
            elif self.JWT_PRIVATE_KEY_PATH and self.JWT_PRIVATE_KEY_PATH.exists():
                self._private_key_content = pydantic.SecretStr(
                    self.JWT_PRIVATE_KEY_PATH.read_text()
                )
            else:
                raise ValueError(
                    "JWT Private Key is not configured "
                    + "(set JWT_PRIVATE_KEY or JWT_PRIVATE_KEY_PATH)"
                )
        return self._private_key_content

    @property
    def public_key(self) -> pydantic.SecretStr:
        """Loads the public key content from path or direct config."""
        if self._public_key_content is None:
            if self.JWT_PUBLIC_KEY:
                self._public_key_content = self.JWT_PUBLIC_KEY
            elif self.JWT_PUBLIC_KEY_PATH and self.JWT_PUBLIC_KEY_PATH.exists():
                self._public_key_content = pydantic.SecretStr(
                    self.JWT_PUBLIC_KEY_PATH.read_text()
                )
            else:
                raise ValueError(
                    "JWT Public Key is not configured "
                    + "(set JWT_PUBLIC_KEY or JWT_PUBLIC_KEY_PATH)"
                )
        return self._public_key_content

    @property
    def cache(self) -> diskcache.Cache | redis.Redis:
        if self._cache:
            return self._cache

        if self.CACHE_URL and self.CACHE_URL.get_secret_value().startswith("redis://"):
            _url = httpx.URL(self.CACHE_URL.get_secret_value())
            logger.info(
                "Initializing Redis cache: "
                + f"{_url.copy_with(username=None, password=None, query=None)}"
            )
            self._cache = redis.Redis.from_url(str(_url))
            try:
                self._cache.ping()
                return self._cache

            except redis.exceptions.ConnectionError as e:
                logger.exception(e)
                logger.error("Failed to connect to Redis cache")

        logger.debug("Using DiskCache as default cache backend")
        _cache_path = pathlib.Path("./.cache").resolve()
        logger.info(f"Initializing DiskCache: {_cache_path}")
        self._cache = diskcache.Cache(_cache_path)

        return self._cache

    @property
    def local_cache(self) -> diskcache.Cache:
        if self._local_cache:
            return self._local_cache

        self._local_cache = diskcache.Cache("./.cache")
        return self._local_cache

    def is_settings_valid(self) -> bool:
        if not (self.JWT_PRIVATE_KEY_PATH and self.JWT_PUBLIC_KEY_PATH) and not (
            self.JWT_PRIVATE_KEY and self.JWT_PUBLIC_KEY
        ):
            return False

        return True

    def is_google_oauth_configured(self) -> bool:
        return (
            self.GOOGLE_CLIENT_ID is not None
            and self.GOOGLE_CLIENT_SECRET is not None
            and self.GOOGLE_REDIRECT_URI is not None
        )

    def is_smtp_configured(self) -> bool:
        return (
            self.SMTP_USERNAME is not None
            and self.SMTP_PASSWORD is not None
            and self.SMTP_FROM is not None
            and self.SMTP_SERVER is not None
        )
