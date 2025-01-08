import enum
import json
import typing
import uuid

import pydantic


class ResourceType(enum.StrEnum):
    PROJECT = "project"


class Resource(pydantic.BaseModel):
    id: typing.Text = pydantic.Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: typing.Text
    type: ResourceType | typing.Text
    name: typing.Text
    description: typing.Text = pydantic.Field(default="")
    metadata: typing.Dict[typing.Text, typing.Any] = pydantic.Field(
        default_factory=dict
    )

    _id: typing.Text | None = pydantic.PrivateAttr(default=None)

    def to_doc(self) -> typing.Dict[typing.Text, typing.Any]:
        return json.loads(self.model_dump_json())


class ResourceCreate(Resource):
    type: ResourceType
    name: typing.Text
    description: typing.Text = pydantic.Field(default="")
    metadata: typing.Dict[typing.Text, typing.Any] = pydantic.Field(
        default_factory=dict
    )

    def to_resource(self, project_id: typing.Text) -> Resource:
        return Resource(
            project_id=project_id,
            type=self.type,
            name=self.name,
            description=self.description,
            metadata=self.metadata,
        )


class ResourceUpdate(Resource):
    description: typing.Text | None = pydantic.Field(default=None)
    metadata: typing.Dict[typing.Text, typing.Any] | None = pydantic.Field(default=None)
