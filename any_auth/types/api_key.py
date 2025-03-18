import time
import typing
from uuid import uuid4

import pydantic
from pydantic import BaseModel, Field


class APIKey(BaseModel):
    id: typing.Text = Field(default_factory=lambda: str(uuid4()))
    name: typing.Text = Field(default="Default API Key Name")
    description: typing.Text = Field(default="")
    user_id: typing.Text
    decorator: typing.Text
    prefix: typing.Text
    salt: typing.Text
    hashed_key: typing.Text
    created_at: int = Field(default_factory=lambda: int(time.time()))
    expires_at: typing.Optional[int] = pydantic.Field(default=None)
    disabled: bool = pydantic.Field(default=False)

    # Private attributes
    _id: typing.Text | None = pydantic.PrivateAttr(default=None)

    @staticmethod
    def generate_plain_api_key(
        length: int = 48, *, decorator: typing.Text = "aa"
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

    @classmethod
    def from_plain_key(
        cls,
        plain_key: typing.Text,
        *,
        user_id: typing.Text,
        expires_at: int | None = None,
        prefix_length: int = 8,
    ) -> "APIKey":
        salt, hashed_key = cls.hash_api_key(plain_key)
        api_key_parts = plain_key.split("-", 1)
        if len(api_key_parts) == 1:
            decorator = ""
            secret = api_key_parts[0]
        else:
            decorator = api_key_parts[0]
            secret = api_key_parts[1]
        prefix = secret[:prefix_length]

        return cls(
            user_id=user_id,
            decorator=decorator,
            prefix=prefix,
            salt=salt,
            hashed_key=hashed_key,
            expires_at=expires_at,
        )

    def verify_api_key(
        self, plain_key: typing.Text, *, iterations: int = 100_000
    ) -> bool:
        from any_auth.utils.auth import verify_api_key

        salt = bytes.fromhex(self.salt)
        return verify_api_key(plain_key, salt, self.hashed_key, iterations)


class APIKeyCreate(BaseModel):
    name: typing.Text | None = Field(default=None)
    description: typing.Text | None = Field(default=None)


class APIKeyUpdate(BaseModel):
    name: typing.Text | None = Field(default=None)
    description: typing.Text | None = Field(default=None)


if __name__ == "__main__":
    api_key = APIKey.generate_plain_api_key()
    api_key_in_db = APIKey.from_plain_key(api_key, user_id="usr_1234567890")
    print(f"API Key: {api_key}")
    print(f"API Key in DB: {api_key_in_db.model_dump_json(indent=2)}")
    print(f"Verify API Key: {api_key_in_db.verify_api_key(api_key)}")
