# tests/backend/test_oauth_client.py
from faker import Faker

from any_auth.backend import BackendClient
from any_auth.types.oauth_client import OAuthClient, OAuthClientCreate


def test_oauth_client_create(
    deps_backend_client_session: BackendClient,
    deps_fake: Faker,
):
    backend_client = deps_backend_client_session

    # Create an OAuth client
    oauth_client_create = OAuthClientCreate.model_validate(
        {
            "name": deps_fake.company(),
            "redirect_uris": [deps_fake.url()],
            "scopes": ["openid", "email", "profile"],
        }
    )
    oauth_client = backend_client.oauth_clients.create(oauth_client_create)
    assert oauth_client is not None
    assert oauth_client.name == oauth_client_create.name
    assert sorted(oauth_client.redirect_uris) == sorted(
        oauth_client_create.redirect_uris
    )
    assert sorted(oauth_client.scopes) == sorted(oauth_client_create.scopes)


def test_oauth_client_retrieve(
    deps_backend_client_session: BackendClient,
    deps_fake: Faker,
):
    backend_client = deps_backend_client_session

    # Create an OAuth client
    oauth_client_create = OAuthClientCreate.model_validate(
        {
            "name": deps_fake.company(),
            "redirect_uris": [deps_fake.url()],
            "scopes": ["openid"],
        }
    )
    oauth_client = backend_client.oauth_clients.create(oauth_client_create)
    assert oauth_client is not None

    # Retrieve the client by client_id
    retrieved = backend_client.oauth_clients.retrieve(oauth_client.client_id)
    assert retrieved is not None
    assert retrieved.client_id == oauth_client.client_id
    assert retrieved.name == oauth_client.name
    assert sorted(retrieved.redirect_uris) == sorted(oauth_client.redirect_uris)


def test_oauth_client_list(
    deps_backend_client_session: BackendClient,
    deps_fake: Faker,
):
    backend_client = deps_backend_client_session

    # Create a few OAuth clients
    for _ in range(3):
        oauth_client_create = OAuthClientCreate.model_validate(
            {
                "name": deps_fake.company(),
                "redirect_uris": [deps_fake.url(), deps_fake.url()],
                "scopes": ["openid", "profile"],
            }
        )
        backend_client.oauth_clients.create(oauth_client_create)

    # List them
    page_oauth_clients = backend_client.oauth_clients.list(limit=5)
    assert len(page_oauth_clients.data) > 0
    for client in page_oauth_clients.data:
        assert isinstance(client, OAuthClient)


def test_oauth_client_disable_and_enable(
    deps_backend_client_session: BackendClient,
    deps_fake: Faker,
):
    backend_client = deps_backend_client_session

    # Create an OAuth client
    oauth_client_create = OAuthClientCreate.model_validate(
        {
            "name": deps_fake.company(),
            "redirect_uris": [deps_fake.url()],
            "scopes": ["openid"],
        }
    )
    oauth_client = backend_client.oauth_clients.create(oauth_client_create)
    assert oauth_client is not None
    assert oauth_client.disabled is False

    # Disable the OAuth client
    disabled_client = backend_client.oauth_clients.set_disabled(
        oauth_client.client_id, disabled=True
    )
    assert disabled_client.disabled is True

    # Enable again
    enabled_client = backend_client.oauth_clients.set_disabled(
        oauth_client.client_id, disabled=False
    )
    assert enabled_client.disabled is False
