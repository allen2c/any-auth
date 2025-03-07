import json
import logging
import time
import typing
import uuid

import pydantic

if typing.TYPE_CHECKING:
    from faker import Faker

    from any_auth.backend import BackendClient
    from any_auth.types.role_assignment import RoleAssignment

logger = logging.getLogger(__name__)


class User(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="ignore")

    id: typing.Text = pydantic.Field(default_factory=lambda: str(uuid.uuid4()))
    username: typing.Text = pydantic.Field(
        ..., pattern=r"^[a-zA-Z0-9_-]+$", min_length=4, max_length=64
    )
    full_name: typing.Text | None = pydantic.Field(default=None)
    email: pydantic.EmailStr = pydantic.Field(...)
    email_verified: bool = pydantic.Field(default=False)
    phone: typing.Text | None = pydantic.Field(default=None)
    phone_verified: bool = pydantic.Field(default=False)
    disabled: bool = pydantic.Field(default=False)
    profile: typing.Text = pydantic.Field(default="")
    picture: typing.Text | None = pydantic.Field(default=None)
    website: typing.Text = pydantic.Field(default="")
    gender: typing.Text = pydantic.Field(default="")
    birthdate: typing.Text = pydantic.Field(default="")
    zoneinfo: typing.Text = pydantic.Field(default="")
    locale: typing.Text = pydantic.Field(default="")
    address: typing.Text = pydantic.Field(default="")
    metadata: typing.Dict[typing.Text, typing.Any] = pydantic.Field(
        default_factory=dict
    )
    created_at: int = pydantic.Field(default_factory=lambda: int(time.time()))
    updated_at: int = pydantic.Field(default_factory=lambda: int(time.time()))

    _id: typing.Text | None = pydantic.PrivateAttr(default=None)

    @classmethod
    def hash_password(cls, password: typing.Text) -> typing.Text:
        from any_auth.utils.auth import hash_password

        return hash_password(password)

    def to_doc(self) -> typing.Dict[typing.Text, typing.Any]:
        return json.loads(self.model_dump_json())

    def ensure_role_assignment(
        self,
        backend_client_session: "BackendClient",
        *,
        role_name_or_id: typing.Text,
        resource_id: typing.Text,
    ) -> "RoleAssignment":
        from any_auth.types.role_assignment import PLATFORM_ID

        if self._id is None:
            raise ValueError("You must create the user first")

        # Validate role
        role = backend_client_session.roles.retrieve_by_name(role_name_or_id)
        if not role:
            role = backend_client_session.roles.retrieve(role_name_or_id)
        if not role:
            raise ValueError(f"Role '{role_name_or_id}' not found")

        # Validate resource
        if resource_id == PLATFORM_ID:
            logger.debug(
                f"Assigning role '{role.name}' to user "
                + f"'{self.username} ({self.id})' on platform resource"
            )
        else:
            resource = backend_client_session.projects.retrieve(resource_id)
            if not resource:
                resource = backend_client_session.organizations.retrieve(resource_id)
            if not resource:
                raise ValueError(f"Resource '{resource_id}' not found")

        # Check if the role is already assigned to the user on the resource
        role_assignments = backend_client_session.role_assignments.retrieve_by_user_id(
            self.id, resource_id=resource_id
        )
        if role_assignments:
            for _role_assignment in role_assignments:
                if _role_assignment.role_id == role.id:
                    logger.debug(
                        f"Role '{role.name}' already assigned to user "
                        + f"'{self.username} ({self.id})' on resource '{resource_id}'"
                    )
                    return _role_assignment

        # Assign the role to the user on the resource
        _role_assignment = backend_client_session.role_assignments.assign_role(
            user_id=self.id, role_id=role.id, resource_id=resource_id
        )
        return _role_assignment


class UserInDB(User):
    hashed_password: typing.Text


class UserCreate(pydantic.BaseModel):
    username: typing.Text = pydantic.Field(
        ..., pattern=r"^[a-zA-Z0-9_-]+$", min_length=4, max_length=64
    )
    full_name: typing.Text | None = pydantic.Field(default=None)
    email: pydantic.EmailStr = pydantic.Field(...)
    phone: typing.Text | None = pydantic.Field(default=None)
    picture: typing.Text | None = pydantic.Field(default=None)
    password: typing.Text = pydantic.Field(
        ...,
        min_length=8,
        max_length=64,
    )
    metadata: typing.Dict[typing.Text, typing.Any] = pydantic.Field(
        default_factory=dict
    )

    @pydantic.field_validator("password")
    def validate_password(cls, v: typing.Text) -> typing.Text:
        import fastapi

        from any_auth.utils.auth import is_valid_password

        if not is_valid_password(v):
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters and at most 64 characters long and contain at least one uppercase letter, one lowercase letter, one digit, and one special character.",  # noqa: E501
            )
        return v

    @classmethod
    def fake(cls, fake: typing.Optional["Faker"] = None) -> "UserCreate":
        if fake is None:
            from faker import Faker

            fake = Faker()

        return cls(
            username=fake.user_name(),
            full_name=fake.name(),
            email=fake.email(),
            password=fake.password(),
        )

    def to_user_in_db(self) -> UserInDB:
        data: typing.Dict = json.loads(self.model_dump_json())
        data["hashed_password"] = UserInDB.hash_password(data.pop("password"))
        return UserInDB.model_validate(data)


class UserUpdate(pydantic.BaseModel):
    full_name: typing.Text | None = pydantic.Field(default=None)
    email: pydantic.EmailStr | None = pydantic.Field(default=None)
    phone: typing.Text | None = pydantic.Field(default=None)
    picture: typing.Text | None = pydantic.Field(default=None)
    metadata: typing.Dict[typing.Text, typing.Any] | None = pydantic.Field(default=None)
