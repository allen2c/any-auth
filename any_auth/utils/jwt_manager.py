import time
import typing
import uuid

import jwt


def get_user_id_from_payload(
    payload: typing.Dict, *, user_id_key: typing.Text = "sub"
) -> typing.Text | None:
    return payload.get(user_id_key)


def raise_if_payload_expired(payload: typing.Dict) -> None:
    exp = payload.get("exp")
    if exp is None:
        raise jwt.InvalidTokenError("Expiration time is missing")
    if time.time() > exp:
        raise jwt.ExpiredSignatureError


def create_jwt_token(
    user_id: typing.Text,
    expires_in: int = 3600,
    *,
    jwt_secret: typing.Text,
    jwt_algorithm: typing.Text,
    now: typing.Optional[int] = None,
    nonce: typing.Optional[typing.Text] = None,
) -> typing.Text:
    """Sign JWT, payload contains sub=user_id, exp=expiration time, iat=issued time"""

    now = now or int(time.time())
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + expires_in,
        "nonce": nonce or str(uuid.uuid4()),
    }
    token = jwt.encode(payload, jwt_secret, algorithm=jwt_algorithm)
    return token


def verify_jwt_token(
    token: typing.Text, *, jwt_secret: typing.Text, jwt_algorithm: typing.Text
) -> typing.Dict:
    """Verify JWT, return payload dict if success, raise jwt exceptions if failed"""

    payload = jwt.decode(token, jwt_secret, algorithms=[jwt_algorithm])
    return payload
