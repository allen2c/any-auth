import time
import typing
import uuid

import pydantic


class ProjectMember(pydantic.BaseModel):
    id: str = pydantic.Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    user_id: str
    joined_at: int = pydantic.Field(default_factory=lambda: int(time.time()))
    disabled: bool = False
    metadata: dict[str, typing.Any] = pydantic.Field(default_factory=dict)

    _id: typing.Text | None = pydantic.PrivateAttr(default=None)

    # To convert to dict/json for storing in Mongo
    def to_doc(self) -> dict[str, typing.Any]:
        return self.model_dump()


class ProjectMemberCreate(pydantic.BaseModel):
    user_id: str
    metadata: dict[str, typing.Any] = pydantic.Field(default_factory=dict)
    # joined_at can be omitted in Create Model, or manually specified

    def to_member(self, project_id: str) -> ProjectMember:
        return ProjectMember(
            project_id=project_id,
            user_id=self.user_id,
            metadata=self.metadata,
        )
