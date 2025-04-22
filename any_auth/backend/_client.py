import logging
import typing
from functools import cached_property

import httpx
import pymongo
import pymongo.server_api

from any_auth.backend.settings import BackendSettings

if typing.TYPE_CHECKING:
    from any_auth.config import Settings

logger = logging.getLogger(__name__)


class BackendClient:
    _db_url: typing.Optional[typing.Text]

    def __init__(
        self,
        *,
        db_client: pymongo.MongoClient | typing.Text,
        settings: typing.Optional["BackendSettings"] = None,
    ):
        if isinstance(db_client, typing.Text):
            self._db_url = db_client
            self._db_client = pymongo.MongoClient(
                db_client, server_api=pymongo.server_api.ServerApi("1")
            )
        else:
            self._db_client = db_client
            self._db_url = None
        self._settings: typing.Final[BackendSettings] = (
            BackendSettings.model_validate_json(settings.model_dump_json())
            if settings is not None
            else BackendSettings()
        )

    @classmethod
    def from_settings(
        cls,
        settings: "Settings",
        *,
        backend_settings: "BackendSettings",
    ):
        _backend_client = BackendClient(
            db_client=pymongo.MongoClient(
                str(httpx.URL(settings.DATABASE_URL.get_secret_value()))
            ),
            settings=backend_settings,
        )

        return _backend_client

    @property
    def settings(self):
        return self._settings

    @property
    def database_client(self):
        return self._db_client

    @property
    def database_url(self) -> typing.Text:
        if self._db_url is None:
            # Try to check the health of the database connection
            try:
                logger.debug("Try to ping database for getting the metadata")
                self.database_client.admin.command("ping")
            except Exception as e:
                logger.exception(e)
                logger.error("Database health check failed")
            _address = self.database_client.address
            if _address is None:
                raise RuntimeError("Database URL is not available")
            host, port = _address
            self._db_url = f"mongodb://{host}:{port}"
        return self._db_url

    @property
    def database(self):
        return self._db_client[self._settings.database]

    @cached_property
    def organizations(self):
        from any_auth.backend.organizations import Organizations

        return Organizations(self)

    @cached_property
    def projects(self):
        from any_auth.backend.projects import Projects

        return Projects(self)

    @cached_property
    def users(self):
        from any_auth.backend.users import Users

        return Users(self)

    @cached_property
    def roles(self):
        from any_auth.backend.roles import Roles

        return Roles(self)

    @cached_property
    def role_assignments(self):
        from any_auth.backend.role_assignments import RoleAssignments

        return RoleAssignments(self)

    @cached_property
    def organization_members(self):
        from any_auth.backend.organization_members import OrganizationMembers

        return OrganizationMembers(self)

    @cached_property
    def project_members(self):
        from any_auth.backend.project_members import ProjectMembers

        return ProjectMembers(self)

    @cached_property
    def invites(self):
        from any_auth.backend.invites import Invites

        return Invites(self)

    @cached_property
    def api_keys(self):
        from any_auth.backend.api_keys import APIKeys

        return APIKeys(self)

    @cached_property
    def oauth_clients(self):
        from any_auth.backend.oauth_client import OAuthClients

        return OAuthClients(self)

    @cached_property
    def oauth2_authorization_codes(self):
        from any_auth.backend.oauth2 import AuthorizationCodes

        return AuthorizationCodes(self)

    @cached_property
    def oauth2_tokens(self):
        from any_auth.backend.oauth2 import OAuth2Tokens

        return OAuth2Tokens(self)

    def touch(self, with_indexes: bool = True):
        logger.debug("Touching backend")

        if with_indexes:
            self.users.create_indexes()
            self.organizations.create_indexes()
            self.projects.create_indexes()
            self.roles.create_indexes()
            self.role_assignments.create_indexes()
            self.organization_members.create_indexes()
            self.project_members.create_indexes()
            self.api_keys.create_indexes()
            self.invites.create_indexes()
            self.oauth_clients.create_indexes()
            self.oauth2_authorization_codes.create_indexes()
            self.oauth2_tokens.create_indexes()

    def close(self):
        logger.debug("Closing backend")
        self._db_client.close()
