import pprint
import typing

from faker import Faker

from any_auth.backend import BackendClient
from any_auth.types.organization import (
    Organization,
    OrganizationCreate,
    OrganizationUpdate,
)

ORGANIZATIONS_CREATE = 3


def test_organizations_create(
    deps_backend_client_session: BackendClient,
    deps_fake: Faker,
):
    backend_client_session = deps_backend_client_session

    page_organizations = backend_client_session.organizations.list()
    assert len(page_organizations.data) == 0

    organizations_create = [
        OrganizationCreate(
            name=deps_fake.user_name(),
            full_name=deps_fake.name(),
            metadata={"test": "test"},
        )
        for _ in range(ORGANIZATIONS_CREATE)
    ]

    for organization_create in organizations_create:
        assert (
            backend_client_session.organizations.create(organization_create) is not None
        )


def test_organizations_get(
    deps_backend_client_session: BackendClient,
):
    backend_client_session = deps_backend_client_session

    # Get all organizations
    has_more = True
    after: typing.Text | None = None
    organizations: typing.List[Organization] = []
    limit = 1
    while has_more:
        page_organizations = backend_client_session.organizations.list(
            after=after, limit=limit
        )
        has_more = page_organizations.has_more
        after = page_organizations.last_id
        assert len(page_organizations.data) == limit
        organizations.extend(page_organizations.data)
    assert len(organizations) == ORGANIZATIONS_CREATE

    # Get organization by id
    organization_id = organizations[0].id
    organization = backend_client_session.organizations.retrieve(organization_id)
    assert organization is not None
    assert organization.id == organization_id

    # Get organization by name
    organization = backend_client_session.organizations.retrieve_by_name(
        organizations[0].name
    )
    assert organization is not None
    assert organization.id == organization_id


def test_organizations_update(
    deps_backend_client_session: BackendClient,
    deps_fake: Faker,
):
    backend_client_session = deps_backend_client_session

    organizations = backend_client_session.organizations.list(limit=1)
    assert len(organizations.data) == 1
    organization = organizations.data[0]

    # Update organization
    organization_update = OrganizationUpdate(
        full_name=deps_fake.name(),
        metadata={"test": "test2"},
    )
    updated_organization = backend_client_session.organizations.update(
        organization.id, organization_update
    )
    assert updated_organization is not None
    assert updated_organization.id == organization.id
    assert updated_organization.full_name == organization_update.full_name
    assert pprint.pformat(updated_organization.metadata) == pprint.pformat(
        organization_update.metadata
    )


def test_organizations_disable(
    deps_backend_client_session: BackendClient,
):
    backend_client_session = deps_backend_client_session

    organizations = backend_client_session.organizations.list(limit=1)
    assert len(organizations.data) == 1
    organization = organizations.data[0]
    assert organization.disabled is False

    # Disable organization
    disabled_organization = backend_client_session.organizations.set_disabled(
        organization.id, disabled=True
    )
    assert disabled_organization.disabled is True

    # Enable organization
    enabled_organization = backend_client_session.organizations.set_disabled(
        organization.id, disabled=False
    )
    assert enabled_organization.disabled is False
