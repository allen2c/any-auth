import random
import typing

from any_auth.backend import BackendClient
from any_auth.config import Settings
from any_auth.types.role import PLATFORM_ROLES, TENANT_ROLES, Role, RoleUpdate


def test_roles_indexes(
    raise_if_not_test_env: None, backend_client_session: BackendClient
):
    backend_client_session.roles.create_indexes()


def test_roles_create(
    raise_if_not_test_env: None, backend_client_session: BackendClient
):
    roles: typing.List[Role] = []
    for predefined_role in PLATFORM_ROLES + TENANT_ROLES:
        roles.append(backend_client_session.roles.create(predefined_role))
    assert len(roles) == len(PLATFORM_ROLES + TENANT_ROLES)


def test_roles_retrieve(
    raise_if_not_test_env: None, backend_client_session: BackendClient
):
    # Retrieve
    role = backend_client_session.roles.retrieve_by_name(
        random.choice(PLATFORM_ROLES).name
    )
    assert role is not None

    # List
    page_roles = backend_client_session.roles.list(
        limit=len(PLATFORM_ROLES + TENANT_ROLES)
    )
    assert len(page_roles.data) == len(PLATFORM_ROLES + TENANT_ROLES)


def test_roles_update(
    raise_if_not_test_env: None, backend_client_session: BackendClient
):
    role = backend_client_session.roles.retrieve_by_name(
        random.choice(PLATFORM_ROLES).name
    )
    assert role is not None

    old_name = role.name
    new_name = Settings.fake.user_name()
    role = backend_client_session.roles.update(role.id, RoleUpdate(name=new_name))
    assert role.name == new_name

    assert backend_client_session.roles.retrieve_by_name(old_name) is None
    assert backend_client_session.roles.retrieve_by_name(new_name) is not None

    role = backend_client_session.roles.update(role.id, RoleUpdate(name=old_name))
    assert role.name == old_name

    assert backend_client_session.roles.retrieve_by_name(new_name) is None
    assert backend_client_session.roles.retrieve_by_name(old_name) is not None


def test_roles_disable(
    raise_if_not_test_env: None, backend_client_session: BackendClient
):
    role = backend_client_session.roles.retrieve_by_name(
        random.choice(PLATFORM_ROLES).name
    )
    assert role is not None

    role = backend_client_session.roles.set_disabled(role.id, True)
    assert role.disabled
    retrieved_role = backend_client_session.roles.retrieve_by_name(role.name)
    assert retrieved_role and retrieved_role.disabled is True

    role = backend_client_session.roles.set_disabled(role.id, False)
    assert role.disabled is False
    retrieved_role = backend_client_session.roles.retrieve_by_name(role.name)
    assert retrieved_role and retrieved_role.disabled is False
