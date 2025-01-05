import enum
import json
import typing
import uuid

import pydantic


class ResourceType(enum.StrEnum):
    PROJECT = "project"


class Resource(pydantic.BaseModel):
    id: typing.Text = pydantic.Field(default_factory=lambda: str(uuid.uuid4()))
    type: ResourceType
    name: typing.Text
    metadata: typing.Dict[typing.Text, typing.Any] = pydantic.Field(
        default_factory=dict
    )

    _id: typing.Text | None = pydantic.PrivateAttr(default=None)

    def to_doc(self) -> typing.Dict[typing.Text, typing.Any]:
        return json.loads(self.model_dump_json())
