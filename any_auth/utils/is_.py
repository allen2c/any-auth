import typing

import pydantic
import pydantic_core
from pydantic import validate_email


def is_email(email: typing.Union[str, pydantic.EmailStr]) -> bool:
    try:
        validate_email(str(email))
        return True
    except pydantic_core.PydanticCustomError:
        return False


if __name__ == "__main__":
    assert is_email("allenchou@gmail.com")
    assert not is_email("allenchou.gmail.com")
