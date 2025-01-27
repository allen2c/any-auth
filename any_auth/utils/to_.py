import enum
import typing

T = typing.TypeVar("T")


def to_enum_value(might_enum_item: enum.Enum | typing.Any) -> typing.Any:
    if isinstance(might_enum_item, enum.Enum):
        return might_enum_item.value
    return might_enum_item
