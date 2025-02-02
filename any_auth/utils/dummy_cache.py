import typing


class DummyCache:
    def __init__(self, *args, **kwargs):
        pass

    def set(
        self,
        key: typing.Text,
        value: typing.Any,
        expire: typing.Optional[int] = None,
        *args,
        **kwargs
    ) -> typing.Any:
        pass

    def get(self, key: typing.Text, *args, **kwargs) -> typing.Any:
        pass

    def delete(self, key: typing.Text, *args, **kwargs) -> typing.Any:
        pass
