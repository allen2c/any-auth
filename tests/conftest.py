import os
import time
import uuid

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
def backend_database_name():
    return f"auth_test_{int(time.time())}_{str(uuid.uuid4())[:8]}"


@pytest.fixture(scope="module")
def backend_database_session(backend_database_name):
    from any_auth.config import Settings

    settings = Settings()  # type: ignore

    client = pymongo.MongoClient(settings.DATABASE_URL.get_secret_value())
    ping_result = client.admin.command("ping")
    assert ping_result["ok"] == 1.0

    db = client[backend_database_name]
    db.list_collection_names()

    yield db

    client.drop_database(backend_database_name)
