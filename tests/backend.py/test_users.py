import typing

from faker import Faker

from any_auth.backend import BackendClient
from any_auth.types.user import UserCreate, UserInDB

USERS_CREATE = 3


def test_users_indexes(
    raise_if_not_test_env: None, backend_client_session: BackendClient
):
    backend_client_session.users.create_indexes()


def test_users_create(
    raise_if_not_test_env: None, backend_client_session: BackendClient, fake: Faker
):
    page_users = backend_client_session.users.list()
    assert len(page_users.data) == 0

    users_create = [
        UserCreate(
            username=fake.user_name(),
            full_name=fake.name(),
            email=fake.email(),
            phone=fake.phone_number(),
            password=fake.password(),
            metadata={"test": "test"},
        )
        for _ in range(USERS_CREATE)
    ]

    for user_create in users_create:
        assert backend_client_session.users.create(user_create) is not None


def test_users_get(raise_if_not_test_env: None, backend_client_session: BackendClient):
    # Get all users
    has_more = True
    after: typing.Text | None = None
    users: typing.List[UserInDB] = []
    limit = 1
    while has_more:
        page_users = backend_client_session.users.list(after=after, limit=limit)
        has_more = page_users.has_more
        after = page_users.last_id
        assert len(page_users.data) == limit
        users.extend(page_users.data)
    assert len(users) == USERS_CREATE

    # Get user by id
    user_id = users[0].id
    user = backend_client_session.users.retrieve(user_id)
    assert user is not None
    assert user.id == user_id
