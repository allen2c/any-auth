import os
import time
import uuid

import httpx
import pymongo
import pytest


@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "true")
    monkeypatch.setenv("IS_TEST", "true")
    monkeypatch.setenv("IS_TESTING", "true")
    monkeypatch.setenv("PYTEST_RUNNING", "true")


@pytest.fixture
def raise_if_not_test_env():
    from any_auth.config import Settings

    settings = Settings()  # type: ignore

    assert os.getenv("IS_TESTING") == "true"
    assert settings.ENVIRONMENT == "test"


@pytest.fixture(scope="module")
def fake():
    from faker import Faker

    return Faker()


@pytest.fixture(scope="module")
def backend_database_name():
    return f"auth_test_{int(time.time())}_{str(uuid.uuid4())[:8]}"


@pytest.fixture(scope="module")
def backend_client_session(backend_database_name):
    from any_auth.backend import BackendClient, BackendSettings
    from any_auth.config import Settings

    settings = Settings()  # type: ignore

    db_url = httpx.URL(settings.DATABASE_URL.get_secret_value())
    hidden_db_url = db_url.copy_with(username=None, password=None, query=None)
    db_client = pymongo.MongoClient(str(db_url))
    print(f"Connecting to '{str(hidden_db_url)}'")
    ping_result = db_client.admin.command("ping")
    print(f"Ping result: {ping_result}")
    assert ping_result["ok"] == 1

    print(f"Connecting to '{backend_database_name}'")
    client = BackendClient(
        db_client,
        BackendSettings(database=backend_database_name),
    )
    client.database.list_collection_names()
    print(f"Database '{backend_database_name}' created")

    yield client

    # Cleanup: Drop all collections instead of the entire database
    for collection_name in client.database.list_collection_names():
        client.database.drop_collection(collection_name)
    print(f"All collections in database '{backend_database_name}' dropped")
