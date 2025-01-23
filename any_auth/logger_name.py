import pathlib
import typing

LOGGER_NAME: typing.Final[typing.Text] = (
    pathlib.Path(__file__).parent.joinpath("LOGGER_NAME").read_text()
).strip()
