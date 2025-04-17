"""
OAuth 2.0 backend implementation for AnyAuth.
"""

import hashlib
import logging
import time
import typing

import fastapi
import pymongo
import pymongo.collection
import pymongo.errors

from any_auth.backend._base import BaseCollection
from any_auth.types.oauth2 import AuthorizationCode, CodeChallengeMethod, OAuth2Token
from any_auth.types.pagination import Page

if typing.TYPE_CHECKING:
    from any_auth.backend._client import BackendClient

logger = logging.getLogger(__name__)


class AuthorizationCodes(BaseCollection):
    """Collection for managing OAuth 2.0 authorization codes."""

    def __init__(self, client: "BackendClient"):
        super().__init__(client)

    @property
    def collection_name(self):
        return "oauth2_authorization_codes"

    def create_indexes(self, *args, **kwargs):
        super().create_indexes(self.settings.indexes_oauth2_authorization_codes)  # type: ignore  # noqa: E501

    def create(self, authorization_code: AuthorizationCode) -> AuthorizationCode:
        """Store a new authorization code."""
        try:
            doc = authorization_code.to_doc()
            result = self.collection.insert_one(doc)
            authorization_code._id = str(result.inserted_id)

            # Cache the authorization code
            self._client.cache.set(
                f"oauth2_code:{authorization_code.code}",
                authorization_code.model_dump_json(),
                int(authorization_code.expires_at - time.time()),
            )

            return authorization_code

        except pymongo.errors.DuplicateKeyError as e:
            raise fastapi.HTTPException(
                status_code=409, detail="Authorization code already exists."
            ) from e

    def retrieve(self, code: str) -> AuthorizationCode | None:
        """Retrieve an authorization code by its value."""
        # Try to get from cache first
        cached_code = self._client.cache.get(f"oauth2_code:{code}")
        if cached_code:
            return AuthorizationCode.model_validate_json(cached_code)  # type: ignore

        # Get from database
        doc = self.collection.find_one({"code": code})
        if not doc:
            return None

        authorization_code = AuthorizationCode.model_validate(doc)
        authorization_code._id = str(doc["_id"])

        # No need to cache here, as codes are short-lived

        return authorization_code

    def use_code(self, code: str) -> AuthorizationCode | None:
        """Mark an authorization code as used."""
        doc = self.collection.find_one_and_update(
            {"code": code, "used": False},
            {"$set": {"used": True}},
            return_document=pymongo.ReturnDocument.AFTER,
        )

        if not doc:
            return None

        authorization_code = AuthorizationCode.model_validate(doc)
        authorization_code._id = str(doc["_id"])

        # Update cache if it exists
        self._client.cache.delete(f"oauth2_code:{code}")

        return authorization_code

    def validate_code_challenge(
        self, code: AuthorizationCode, code_verifier: str
    ) -> bool:
        """
        Validate PKCE code_verifier against stored code_challenge.
        """
        if not code.code_challenge or not code.code_challenge_method:
            # PKCE was not used with this code
            return True

        if not code_verifier:
            return False

        if code.code_challenge_method == CodeChallengeMethod.PLAIN:
            return code.code_challenge == code_verifier

        if code.code_challenge_method == CodeChallengeMethod.S256:
            challenge = hashlib.sha256(code_verifier.encode()).digest()
            challenge_b64 = challenge.hex()
            return code.code_challenge == challenge_b64

        # Unsupported method
        return False


class OAuth2Tokens(BaseCollection):
    """Collection for managing OAuth 2.0 tokens."""

    def __init__(self, client: "BackendClient"):
        super().__init__(client)

    @property
    def collection_name(self):
        return "oauth2_tokens"

    def create_indexes(self, *args, **kwargs):
        super().create_indexes(self.settings.indexes_oauth2_tokens)

    def create(self, token: OAuth2Token) -> OAuth2Token:
        """Store a new OAuth2 token."""
        try:
            doc = token.to_doc()
            result = self.collection.insert_one(doc)
            token._id = str(result.inserted_id)

            # Cache the access token and refresh token
            access_token_ttl = int(token.expires_at - time.time())
            self._client.cache.set(
                f"oauth2_access_token:{token.access_token}",
                token.model_dump_json(),
                access_token_ttl,
            )

            if token.refresh_token:
                # Refresh tokens typically have longer validity
                refresh_token_ttl = 30 * 24 * 60 * 60  # 30 days
                self._client.cache.set(
                    f"oauth2_refresh_token:{token.refresh_token}",
                    token.model_dump_json(),
                    refresh_token_ttl,
                )

            return token

        except pymongo.errors.DuplicateKeyError as e:
            raise fastapi.HTTPException(
                status_code=409, detail="Token already exists."
            ) from e

    def retrieve_by_access_token(self, access_token: str) -> OAuth2Token | None:
        """Retrieve a token by its access token value."""
        # Try to get from cache first
        cached_token = self._client.cache.get(f"oauth2_access_token:{access_token}")
        if cached_token:
            return OAuth2Token.model_validate_json(cached_token)  # type: ignore

        # Get from database
        doc = self.collection.find_one({"access_token": access_token})
        if not doc:
            return None

        token = OAuth2Token.model_validate(doc)
        token._id = str(doc["_id"])

        # Cache the token
        access_token_ttl = max(1, int(token.expires_at - time.time()))
        self._client.cache.set(
            f"oauth2_access_token:{access_token}",
            token.model_dump_json(),
            access_token_ttl,
        )

        return token

    def retrieve_by_refresh_token(self, refresh_token: str) -> OAuth2Token | None:
        """Retrieve a token by its refresh token value."""
        # Try to get from cache first
        cached_token = self._client.cache.get(f"oauth2_refresh_token:{refresh_token}")
        if cached_token:
            return OAuth2Token.model_validate_json(cached_token)  # type: ignore

        # Get from database
        doc = self.collection.find_one({"refresh_token": refresh_token})
        if not doc:
            return None

        token = OAuth2Token.model_validate(doc)
        token._id = str(doc["_id"])

        return token

    def revoke_token(
        self, token_value: str, token_type_hint: str | None = None
    ) -> bool:
        """
        Revoke an access or refresh token.

        Args:
            token_value: The token to revoke
            token_type_hint: Optional hint about the token type ('access_token' or 'refresh_token')

        Returns:
            True if a token was revoked, False otherwise
        """  # noqa: E501

        # Determine the token type if not hinted
        query = {}
        if token_type_hint == "access_token":
            query["access_token"] = token_value
        elif token_type_hint == "refresh_token":
            query["refresh_token"] = token_value
        else:
            # Try both
            query = {
                "$or": [{"access_token": token_value}, {"refresh_token": token_value}]
            }

        doc = self.collection.find_one_and_update(
            query,
            {"$set": {"revoked": True}},
            return_document=pymongo.ReturnDocument.AFTER,
        )

        if not doc:
            return False

        # Clear cache
        token = OAuth2Token.model_validate(doc)
        self._client.cache.delete(f"oauth2_access_token:{token.access_token}")
        if token.refresh_token:
            self._client.cache.delete(f"oauth2_refresh_token:{token.refresh_token}")

        return True

    def list_by_user_id(
        self,
        user_id: str,
        limit: int = 20,
        skip: int = 0,
    ) -> Page[OAuth2Token]:
        """Get all tokens for a user."""
        cursor = (
            self.collection.find({"user_id": user_id})
            .sort("issued_at", -1)
            .skip(skip)
            .limit(limit + 1)
        )

        docs = list(cursor)
        has_more = len(docs) > limit

        if has_more:
            docs = docs[:limit]

        tokens = []
        for doc in docs:
            token = OAuth2Token.model_validate(doc)
            token._id = str(doc["_id"])
            tokens.append(token)

        first_id = tokens[0].id if tokens else None
        last_id = tokens[-1].id if tokens else None

        return Page[OAuth2Token](
            data=tokens,
            first_id=first_id,
            last_id=last_id,
            has_more=has_more,
        )

    def list_by_client_id(
        self,
        client_id: str,
        limit: int = 20,
        skip: int = 0,
    ) -> Page[OAuth2Token]:
        """Get all tokens for a client."""
        cursor = (
            self.collection.find({"client_id": client_id})
            .sort("issued_at", -1)
            .skip(skip)
            .limit(limit + 1)
        )

        docs = list(cursor)
        has_more = len(docs) > limit

        if has_more:
            docs = docs[:limit]

        tokens = []
        for doc in docs:
            token = OAuth2Token.model_validate(doc)
            token._id = str(doc["_id"])
            tokens.append(token)

        first_id = tokens[0].id if tokens else None
        last_id = tokens[-1].id if tokens else None

        return Page[OAuth2Token](
            data=tokens,
            first_id=first_id,
            last_id=last_id,
            has_more=has_more,
        )
