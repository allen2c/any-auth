# scripts/get_started/ensure_app_all_roles.py
# use terminal
import logging
import sys

from logging_bullet_train import set_logger

from any_auth.backend import BackendClient, BackendSettings
from any_auth.config import Settings
from any_auth.logger_name import LOGGER_NAME
from any_auth.types.role import ALL_ROLES, Role, RoleCreate

logger = logging.getLogger(__name__)

SILENT = "--silent" in sys.argv

if not SILENT:
    set_logger(logger, level=logging.DEBUG)
    set_logger(LOGGER_NAME, level=logging.DEBUG)


def ensure_role(backend_client: BackendClient, *, role_create: RoleCreate) -> Role:
    might_role = backend_client.roles.retrieve_by_name(role_create.name)

    if might_role is None:
        logger.debug(f"Role not found, creating: {role_create.model_dump_json()}")
        role = backend_client.roles.create(role_create)
        logger.info(f"Role created: {role.model_dump_json()}")
    else:
        role = might_role

    logger.debug(f"Role retrieved: {role.model_dump_json()}")
    return role


def main():
    settings = Settings()  # type: ignore

    backend_client = BackendClient.from_settings(
        settings, backend_settings=BackendSettings.from_any_auth_settings(settings)
    )
    logger.info(f"Connected to database: '{backend_client.database_url}'")

    for role_create in ALL_ROLES:
        ensure_role(backend_client, role_create=role_create)


if __name__ == "__main__":
    main()
