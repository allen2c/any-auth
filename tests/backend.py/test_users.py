import typing

from any_auth.backend import BackendClient, BackendSettings
from any_auth.config import Settings


def test_users_indexes(
    raise_if_not_test_env: None, backend_database_session: typing.Text
):
    settings = Settings()  # type: ignore
    client = BackendClient(
        settings.DATABASE_URL.get_secret_value(),
        BackendSettings(database=backend_database_session),
    )
    client.users.create_indexes()


def test_users_create(
    raise_if_not_test_env: None, backend_database_session: typing.Text
):
    settings = Settings()  # type: ignore
    client = BackendClient(
        settings.DATABASE_URL.get_secret_value(),
        BackendSettings(database=backend_database_session),
    )

    page_users = client.users.list()
    assert len(page_users.data) == 0
