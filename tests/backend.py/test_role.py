import random
import typing

from any_auth.backend import BackendClient
from any_auth.config import Settings
from any_auth.types.role import (
    PLATFORM_CREATOR_ROLE,
    PLATFORM_MANAGER_ROLE,
    PLATFORM_ROLES,
    TENANT_ROLES,
    Role,
    RoleUpdate,
)


def test_roles_create(deps_backend_client_session: BackendClient):
    backend_client_session = deps_backend_client_session

    roles: typing.List[Role] = []
    for predefined_role in PLATFORM_ROLES + TENANT_ROLES:
        roles.append(backend_client_session.roles.create(predefined_role))
    assert len(roles) == len(PLATFORM_ROLES + TENANT_ROLES)


def test_roles_retrieve(deps_backend_client_session: BackendClient):
    backend_client_session = deps_backend_client_session

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

    # Retrieve the PLATFORM_MANAGER_ROLE using its name.
    # This ensures that the role exists and can be identified.
    role = backend_client_session.roles.retrieve_by_id_or_name(
        PLATFORM_MANAGER_ROLE.name
    )
    assert role is not None, "Platform manager role not found"

    # Retrieve all child roles under the PLATFORM_MANAGER_ROLE.
    # Since the platform manager role is expected to have subordinate roles,
    # we assert that at least one child role is returned.
    child_roles = backend_client_session.roles.retrieve_all_child_roles(role.id)
    assert (
        len(child_roles) > 0
    ), "Expected at least one child role for the platform manager role"

    # Retrieve the PLATFORM_CREATOR_ROLE using its name.
    # This ensures that the creator role exists in the system.
    role = backend_client_session.roles.retrieve_by_id_or_name(
        PLATFORM_CREATOR_ROLE.name
    )
    assert role is not None, "Platform creator role not found"

    # Retrieve all child roles under the PLATFORM_CREATOR_ROLE.
    # In this case, the platform creator role is expected to have no child roles,
    # so we assert that the list of child roles is empty.
    child_roles = backend_client_session.roles.retrieve_all_child_roles(role.id)
    assert (
        len(child_roles) == 0
    ), "Expected no child roles for the platform creator role"


def test_roles_update(deps_backend_client_session: BackendClient):
    backend_client_session = deps_backend_client_session

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


def test_roles_disable(deps_backend_client_session: BackendClient):
    backend_client_session = deps_backend_client_session

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
