import json
import re
import time
import typing
import uuid

import pydantic

if typing.TYPE_CHECKING:
    from faker import Faker


class Project(pydantic.BaseModel):
    id: typing.Text = pydantic.Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: typing.Text | None = pydantic.Field(default=None)
    name: typing.Text = pydantic.Field(
        ..., pattern=r"^[a-zA-Z0-9_-]+$", min_length=4, max_length=64
    )
    full_name: typing.Text | None = pydantic.Field(default=None)
    disabled: bool = pydantic.Field(default=False)
    metadata: typing.Dict[typing.Text, typing.Any] = pydantic.Field(
        default_factory=dict
    )
    created_by: typing.Text = pydantic.Field(...)
    created_at: int = pydantic.Field(default_factory=lambda: int(time.time()))
    updated_at: int = pydantic.Field(default_factory=lambda: int(time.time()))

    _id: typing.Text | None = pydantic.PrivateAttr(default=None)

    @property
    def no_organization(self) -> bool:
        return self.organization_id is None

    def to_doc(self) -> typing.Dict[typing.Text, typing.Any]:
        return json.loads(self.model_dump_json())


class ProjectCreate(pydantic.BaseModel):
    name: typing.Text
    full_name: typing.Text | None = pydantic.Field(default=None)
    metadata: typing.Dict[typing.Text, typing.Any] = pydantic.Field(
        default_factory=dict
    )

    @classmethod
    def fake(
        cls, name: typing.Text | None = None, *, fake: typing.Optional["Faker"] = None
    ) -> "ProjectCreate":
        if fake is None:
            from faker import Faker

            fake = Faker()

        if name is None:
            project_full_name = fake.company()
            project_name = re.sub(r"[^a-zA-Z0-9_-]", "", project_full_name)
        else:
            project_full_name = project_name = name

        return cls(
            name=project_name, full_name=project_full_name, metadata={"test": "test"}
        )

    def to_project(
        self, *, organization_id: typing.Text | None = None, created_by: typing.Text
    ) -> Project:
        return Project(
            organization_id=organization_id,
            name=self.name,
            full_name=self.full_name,
            metadata=self.metadata,
            created_by=created_by,
        )


class ProjectUpdate(pydantic.BaseModel):
    full_name: typing.Text | None = pydantic.Field(default=None)
    metadata: typing.Dict[typing.Text, typing.Any] | None = pydantic.Field(default=None)
