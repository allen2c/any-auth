import time
import typing

import jwt


def create_jwt_token(
    user_id: typing.Text,
    expires_in: int = 3600,
    *,
    jwt_secret: typing.Text,
    jwt_algorithm: typing.Text
) -> typing.Text:
    """Sign JWT, payload contains sub=user_id, exp=expiration time, iat=issued time"""

    now = int(time.time())
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + expires_in,
    }
    token = jwt.encode(payload, jwt_secret, algorithm=jwt_algorithm)
    return token


def verify_jwt_token(
    token: typing.Text, *, jwt_secret: typing.Text, jwt_algorithm: typing.Text
) -> typing.Dict:
    """Verify JWT, return payload dict if success, raise jwt exceptions if failed"""

    payload = jwt.decode(token, jwt_secret, algorithms=[jwt_algorithm])
    return payload
