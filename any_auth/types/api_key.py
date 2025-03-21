import secrets
import time
import typing
import uuid

import pydantic
from pydantic import BaseModel, Field

DEFAULT_DECORATOR = "au"
DEFAULT_PREFIX_LENGTH = 8


class APIKey(BaseModel):
    id: typing.Text = Field(default_factory=lambda: str(uuid.uuid4()))
    resource_id: typing.Text
    name: typing.Text = Field(default="Default API Key Name")
    description: typing.Text = Field(default="")
    created_by: typing.Text
    created_at: int = Field(default_factory=lambda: int(time.time()))
    expires_at: typing.Optional[int] = pydantic.Field(default=None)

    @staticmethod
    def generate_plain_api_key(
        length: int = 48, *, decorator: typing.Text = DEFAULT_DECORATOR
    ) -> str:
        from any_auth.utils.auth import generate_api_key

        return generate_api_key(length, decorator=decorator)

    @staticmethod
    def hash_api_key(
        plain_key: typing.Text, *, iterations: int = 100_000
    ) -> typing.Tuple[typing.Text, typing.Text]:
        from any_auth.utils.auth import generate_salt, hash_api_key

        salt = generate_salt(16)
        return salt.hex(), hash_api_key(plain_key, salt, iterations)


class APIKeyInDB(APIKey):
    decorator: typing.Text
    prefix: typing.Text
    salt: typing.Text
    hashed_key: typing.Text

    # Private attributes
    _id: typing.Text | None = pydantic.PrivateAttr(default=None)  # DB ID

    @classmethod
    def from_plain_key(
        cls,
        plain_key: typing.Text,
        *,
        resource_id: typing.Text,
        name: typing.Text | None = None,
        description: typing.Text | None = None,
        created_by: typing.Text,
        expires_at: int | None = None,
        prefix_length: int = DEFAULT_PREFIX_LENGTH,
    ) -> "typing.Self":
        salt, hashed_key = cls.hash_api_key(plain_key)
        api_key_parts = plain_key.split("-", 1)
        if len(api_key_parts) == 1:
            decorator = ""
            secret = api_key_parts[0]
        else:
            decorator = api_key_parts[0]
            secret = api_key_parts[1]
        prefix = secret[:prefix_length]

        api_key = cls(
            resource_id=resource_id,
            created_by=created_by,
            decorator=decorator,
            prefix=prefix,
            salt=salt,
            hashed_key=hashed_key,
            expires_at=expires_at,
        )
        if name and name.strip():
            api_key.name = name.strip()
        if description and description.strip():
            api_key.description = description.strip()
        return api_key

    def verify_api_key(
        self, plain_key: typing.Text, *, iterations: int = 100_000
    ) -> bool:
        from any_auth.utils.auth import verify_api_key

        salt = bytes.fromhex(self.salt)
        return verify_api_key(plain_key, salt, self.hashed_key, iterations)


class APIKeyCreate(BaseModel):
    name: typing.Text = Field(default_factory=lambda: f"API-Key-{secrets.token_hex(8)}")
    description: typing.Text = Field(default="")
    expires_at: typing.Optional[int] = Field(default=None)

    def to_api_key(
        self,
        *,
        resource_id: typing.Text,
        created_by: typing.Text,
        plain_key: typing.Text | None = None,
    ) -> APIKeyInDB:
        _plain_key = plain_key or APIKey.generate_plain_api_key()
        return APIKeyInDB.from_plain_key(
            _plain_key,
            resource_id=resource_id,
            created_by=created_by,
            name=self.name,
            description=self.description,
            expires_at=self.expires_at,
        )


class APIKeyUpdate(BaseModel):
    name: typing.Text | None = Field(default=None)
    description: typing.Text | None = Field(default=None)
    expires_at: typing.Optional[int] = Field(default=None)


if __name__ == "__main__":
    api_key = APIKey.generate_plain_api_key()
    api_key_in_db = APIKeyInDB.from_plain_key(
        api_key, created_by="usr_1234567890", resource_id="proj_1234567890"
    )
    print(f"API Key: {api_key}")
    print(f"API Key in DB: {api_key_in_db.model_dump_json(indent=2)}")
    print(f"Verify API Key: {api_key_in_db.verify_api_key(api_key)}")
