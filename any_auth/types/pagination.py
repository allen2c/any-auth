import typing

import pydantic

T = typing.TypeVar("T")


class Page(pydantic.BaseModel, typing.Generic[T]):
    object: typing.Literal["list"] = pydantic.Field(default="list")
    data: typing.List[T]
    first_id: typing.Optional[str] = None
    last_id: typing.Optional[str] = None
    has_more: bool = False
