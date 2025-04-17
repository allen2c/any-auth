import json
import pathlib
import time
import typing
import uuid
from types import MappingProxyType

import pydantic
import yaml

from .permission import Permission

PLATFORM_MANAGER_ROLE_NAME: typing.Final[typing.Text] = "PlatformManager"
PLATFORM_CREATOR_ROLE_NAME: typing.Final[typing.Text] = "PlatformCreator"
ORG_OWNER_ROLE_NAME: typing.Final[typing.Text] = "OrganizationOwner"
ORG_EDITOR_ROLE_NAME: typing.Final[typing.Text] = "OrganizationEditor"
ORG_VIEWER_ROLE_NAME: typing.Final[typing.Text] = "OrganizationViewer"
PROJECT_OWNER_ROLE_NAME: typing.Final[typing.Text] = "ProjectOwner"
PROJECT_EDITOR_ROLE_NAME: typing.Final[typing.Text] = "ProjectEditor"
PROJECT_VIEWER_ROLE_NAME: typing.Final[typing.Text] = "ProjectViewer"
NA_ROLE_NAME: typing.Final[typing.Text] = "N/A"


class Role(pydantic.BaseModel):
    id: typing.Text = pydantic.Field(default_factory=lambda: str(uuid.uuid4()))
    name: typing.Text
    permissions: typing.List[typing.Union[Permission, typing.Text]] = pydantic.Field(
        default_factory=list
    )
    description: typing.Text | None = pydantic.Field(default=None)
    disabled: bool = pydantic.Field(default=False)
    parent_id: typing.Text | None = pydantic.Field(default=None)
    created_at: int = pydantic.Field(default_factory=lambda: int(time.time()))
    updated_at: int = pydantic.Field(default_factory=lambda: int(time.time()))

    _id: typing.Text | None = pydantic.PrivateAttr(default=None)

    def to_doc(self) -> typing.Dict[typing.Text, typing.Any]:
        return json.loads(self.model_dump_json())


RoleList: typing.TypeAlias = list[Role]
RoleListAdapter = pydantic.TypeAdapter(RoleList)


class RoleCreate(pydantic.BaseModel):
    name: (
        typing.Literal[
            "PlatformManager",
            "PlatformCreator",
            "OrganizationOwner",
            "OrganizationEditor",
            "OrganizationViewer",
            "ProjectOwner",
            "ProjectEditor",
            "ProjectViewer",
            "N/A",
        ]
        | typing.Text
    )
    permissions: typing.List[typing.Union[Permission, typing.Text]] = pydantic.Field(
        default_factory=list
    )
    description: typing.Text | None = pydantic.Field(default=None)
    disabled: bool = pydantic.Field(default=False)
    parent_id: typing.Text | None = pydantic.Field(default=None)

    def to_role(self) -> Role:
        return Role(
            name=self.name,
            permissions=self.permissions,
            description=self.description,
            parent_id=self.parent_id,
        )


class RoleUpdate(pydantic.BaseModel):
    name: typing.Text | None = pydantic.Field(default=None)
    permissions: typing.List[typing.Union[Permission, typing.Text]] | None = (
        pydantic.Field(default=None)
    )
    description: typing.Text | None = pydantic.Field(default=None)
    # The `parent_id` field is not allowed to be updated.
    # This is to prevent cycles in the role hierarchy.


_roles_definitions_raw = yaml.safe_load(
    pathlib.Path(__file__).parent.joinpath("roles.yml").read_text()
)
ROLES_DEFINITIONS: typing.Final[MappingProxyType[typing.Text, RoleCreate]] = (
    MappingProxyType(
        {
            role["name"]: RoleCreate.model_validate(role)
            for role in _roles_definitions_raw["roles"]
        }
    )
)


PLATFORM_MANAGER_ROLE = ROLES_DEFINITIONS[PLATFORM_MANAGER_ROLE_NAME]
PLATFORM_CREATOR_ROLE = ROLES_DEFINITIONS[PLATFORM_CREATOR_ROLE_NAME]
ORG_OWNER_ROLE = ROLES_DEFINITIONS[ORG_OWNER_ROLE_NAME]
ORG_EDITOR_ROLE = ROLES_DEFINITIONS[ORG_EDITOR_ROLE_NAME]
ORG_VIEWER_ROLE = ROLES_DEFINITIONS[ORG_VIEWER_ROLE_NAME]
PROJECT_OWNER_ROLE = ROLES_DEFINITIONS[PROJECT_OWNER_ROLE_NAME]
PROJECT_EDITOR_ROLE = ROLES_DEFINITIONS[PROJECT_EDITOR_ROLE_NAME]
PROJECT_VIEWER_ROLE = ROLES_DEFINITIONS[PROJECT_VIEWER_ROLE_NAME]
NA_ROLE = ROLES_DEFINITIONS[NA_ROLE_NAME]


PLATFORM_ROLES: typing.Final = (
    PLATFORM_MANAGER_ROLE,
    PLATFORM_CREATOR_ROLE,
)
TENANT_ROLES: typing.Final = (
    ORG_OWNER_ROLE,
    ORG_EDITOR_ROLE,
    ORG_VIEWER_ROLE,
    PROJECT_OWNER_ROLE,
    PROJECT_EDITOR_ROLE,
    PROJECT_VIEWER_ROLE,
)
ALL_ROLES: typing.Final = PLATFORM_ROLES + TENANT_ROLES


def check_for_cycles(
    roles: typing.Iterable[Role] | typing.Iterable[RoleCreate],
    field: typing.Literal["name", "id"] = "name",
) -> bool:
    # Create a mapping of role names to their parent_id
    role_hierarchy = {getattr(role, field): role.parent_id for role in roles}

    def has_cycle(role_name, visited):
        if role_name in visited:
            return True
        parent_id = role_hierarchy.get(role_name)
        if parent_id is None:
            return False
        visited.add(role_name)
        return has_cycle(parent_id, visited)

    for role in roles:
        if has_cycle(getattr(role, field), set()):
            return True
    return False


# Check for cycles
if check_for_cycles(ALL_ROLES, field="name"):
    raise ValueError("Pre-defined roles contain a cycle in the hierarchy")


if __name__ == "__main__":
    print(f"There are {len(ALL_ROLES)} pre-defined roles")
    print(f"There are {len(Permission.all())} permissions")
