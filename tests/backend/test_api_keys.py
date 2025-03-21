import pprint
import typing

from faker import Faker

from any_auth.backend import BackendClient
from any_auth.types.api_key import (
    APIKey,
    APIKeyCreate,
    APIKeyUpdate,
)

API_KEYS_CREATE = 3

TEST_RESOURCE_ID = "proj_123"
TEST_USER_ID = "user_123"


def test_api_keys_create(
    deps_backend_client_session: BackendClient,
    deps_fake: Faker,
):
    backend_client_session = deps_backend_client_session

    page_api_keys = backend_client_session.api_keys.list()
    assert len(page_api_keys.data) == 0

    api_keys_create = [
        APIKeyCreate(
            name=deps_fake.user_name(),
            description=deps_fake.text(),
        )
        for _ in range(API_KEYS_CREATE)
    ]

    for api_key_create in api_keys_create:
        assert (
            backend_client_session.api_keys.create(
                api_key_create,
                resource_id=TEST_RESOURCE_ID,
                created_by=TEST_USER_ID,
            )
            is not None
        )


def test_api_keys_get(
    deps_backend_client_session: BackendClient,
):
    backend_client_session = deps_backend_client_session

    # Get all api keys
    has_more = True
    after: typing.Text | None = None
    api_keys: typing.List[APIKey] = []
    limit = 1
    while has_more:
        page_api_keys = backend_client_session.api_keys.list(after=after, limit=limit)
        has_more = page_api_keys.has_more
        after = page_api_keys.last_id
        assert len(page_api_keys.data) == limit
        api_keys.extend(page_api_keys.data)
    assert len(api_keys) == API_KEYS_CREATE

    # Get api key by id
    api_key_id = api_keys[0].id
    api_key = backend_client_session.api_keys.retrieve(api_key_id)
    assert api_key is not None
    assert api_key.id == api_key_id


def test_api_keys_update(
    deps_backend_client_session: BackendClient,
    deps_fake: Faker,
):
    backend_client_session = deps_backend_client_session

    api_keys = backend_client_session.api_keys.list(limit=1)
    assert len(api_keys.data) == 1
    api_key = api_keys.data[0]

    # Update api key
    api_key_update = APIKeyUpdate(
        name=deps_fake.user_name(),
        description=deps_fake.text(),
    )
    updated_api_key = backend_client_session.api_keys.update(api_key.id, api_key_update)
    assert updated_api_key is not None
    assert updated_api_key.id == api_key.id
    assert updated_api_key.name == api_key_update.name
    assert pprint.pformat(updated_api_key.description) == pprint.pformat(
        api_key_update.description
    )


def test_api_keys_delete(
    deps_backend_client_session: BackendClient,
):
    backend_client_session = deps_backend_client_session

    api_keys = backend_client_session.api_keys.list(limit=1)
    assert len(api_keys.data) == 1
    api_key = api_keys.data[0]
    assert api_key is not None

    # Disable api key
    backend_client_session.api_keys.delete(api_key.id)

    # Get api key by id
    api_key = backend_client_session.api_keys.retrieve(api_key.id)
    assert api_key is None


def test_api_keys_retrieve_by_plain_key(
    deps_backend_client_session: BackendClient,
    deps_fake: Faker,
):
    backend_client_session = deps_backend_client_session

    plain_key = APIKey.generate_plain_api_key()

    created_api_key = backend_client_session.api_keys.create(
        APIKeyCreate(
            name=deps_fake.user_name(),
            description=deps_fake.text(),
        ),
        resource_id=TEST_RESOURCE_ID,
        created_by=TEST_USER_ID,
        plain_key=plain_key,
    )
    assert created_api_key is not None

    retrieved_api_key = backend_client_session.api_keys.retrieve_by_plain_key(plain_key)
    assert retrieved_api_key is not None
    assert retrieved_api_key.id == created_api_key.id
    assert retrieved_api_key.name == created_api_key.name
    assert retrieved_api_key.description == created_api_key.description
    assert retrieved_api_key.verify_api_key(plain_key) is True
