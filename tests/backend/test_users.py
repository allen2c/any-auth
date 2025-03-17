import pprint
import typing

from faker import Faker

from any_auth.backend import BackendClient
from any_auth.types.user import UserCreate, UserInDB, UserUpdate

USERS_CREATE = 3


def test_users_create(
    deps_backend_client_session: BackendClient,
    deps_fake: Faker,
):
    backend_client_session = deps_backend_client_session

    page_users = backend_client_session.users.list()
    assert len(page_users.data) == 0

    users_create = [
        UserCreate(
            username=deps_fake.user_name(),
            full_name=deps_fake.name(),
            email=deps_fake.email(),
            phone=deps_fake.phone_number(),
            password=deps_fake.password(),
            metadata={"test": "test"},
        )
        for _ in range(USERS_CREATE)
    ]

    for user_create in users_create:
        assert backend_client_session.users.create(user_create) is not None


def test_users_get(deps_backend_client_session: BackendClient):
    backend_client_session = deps_backend_client_session

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

    # Get user by username
    user = backend_client_session.users.retrieve_by_username(users[0].username)
    assert user is not None
    assert user.id == user_id

    # Get user by email
    user = backend_client_session.users.retrieve_by_email(users[0].email)
    assert user is not None
    assert user.id == user_id


def test_users_update(
    deps_backend_client_session: BackendClient,
    deps_fake: Faker,
):
    backend_client_session = deps_backend_client_session

    users = backend_client_session.users.list(limit=1)
    assert len(users.data) == 1
    user = users.data[0]

    # Update user
    user_update = UserUpdate(
        full_name=deps_fake.name(),
        metadata={"test": "test2"},
    )
    updated_user = backend_client_session.users.update(user.id, user_update)
    assert updated_user is not None
    assert updated_user.id == user.id
    assert updated_user.full_name == user_update.full_name
    assert pprint.pformat(updated_user.metadata) == pprint.pformat(user_update.metadata)


def test_users_disable(
    deps_backend_client_session: BackendClient,
):
    backend_client_session = deps_backend_client_session

    users = backend_client_session.users.list(limit=1)
    assert len(users.data) == 1
    user = users.data[0]
    assert user.disabled is False

    # Disable user
    disabled_user = backend_client_session.users.set_disabled(user.id, disabled=True)
    assert disabled_user.disabled is True

    # Enable user
    enabled_user = backend_client_session.users.set_disabled(user.id, disabled=False)
    assert enabled_user.disabled is False
