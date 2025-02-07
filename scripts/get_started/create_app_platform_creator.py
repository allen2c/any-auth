import logging
import os
import sys
import uuid

from logging_bullet_train import set_logger

from any_auth.backend import BackendClient, BackendSettings
from any_auth.config import Settings
from any_auth.logger_name import LOGGER_NAME
from any_auth.types.role import PLATFORM_CREATOR_ROLE, Role
from any_auth.types.role_assignment import (
    PLATFORM_ID,
    RoleAssignment,
    RoleAssignmentCreate,
)
from any_auth.types.user import UserCreate, UserInDB

logger = logging.getLogger(__name__)

VERBOSE = "--verbose" in sys.argv
SHORT_OUTPUT = "--short" in sys.argv or "-s" in sys.argv

if VERBOSE:
    set_logger(logger, level=logging.DEBUG)
    set_logger(LOGGER_NAME, level=logging.DEBUG)


def ensure_role_platform_creator(backend_client: BackendClient) -> Role:
    might_role_platform_creator = backend_client.roles.retrieve_by_name(
        PLATFORM_CREATOR_ROLE.name
    )

    if might_role_platform_creator is None:
        role_platform_creator = backend_client.roles.create(PLATFORM_CREATOR_ROLE)
        logger.info(f"Role created: {role_platform_creator.model_dump_json()}")
    else:
        role_platform_creator = might_role_platform_creator

    logger.info(f"Role retrieved: {role_platform_creator.model_dump_json()}")
    return role_platform_creator


def create_user_platform_creator(
    backend_client: BackendClient, *, password: str
) -> UserInDB:
    _postfix = str(uuid.uuid4()).replace("-", "")
    user_create = UserCreate(
        username=f"platform-creator-{_postfix}",
        email=f"platform-creator-{_postfix}@anyauth.dev",
        password=password,
        metadata={"script_runner": os.uname().nodename},
    )

    user = backend_client.users.create(user_create)
    logger.info(f"User created: {user.model_dump_json()}")

    return user


def assign_role_platform_creator(
    backend_client: BackendClient, *, user: UserInDB, role_platform_creator: Role
) -> RoleAssignment:
    role_assignment = backend_client.role_assignments.create(
        role_assignment_create=RoleAssignmentCreate(
            user_id=user.id,
            role_id=role_platform_creator.id,
            resource_id=PLATFORM_ID,
        )
    )
    logger.info(f"Role assignment created: {role_assignment.model_dump_json()}")
    return role_assignment


def main():
    settings = Settings()  # type: ignore

    backend_client = BackendClient.from_settings(
        settings, backend_settings=BackendSettings.from_settings(settings)
    )

    role_platform_creator = ensure_role_platform_creator(backend_client)
    password = Settings.fake.password()
    user = create_user_platform_creator(backend_client, password=password)
    assign_role_platform_creator(
        backend_client, user=user, role_platform_creator=role_platform_creator
    )

    if SHORT_OUTPUT:
        print(user.username)
        print(password)
    else:
        print(f"User created: {user.model_dump_json()}")
        print(f"Password: {password}")


if __name__ == "__main__":
    main()
