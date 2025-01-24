import typing

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import any_auth.deps.app_state as AppState
from any_auth.config import Settings
from any_auth.utils.jwt_manager import verify_jwt_token

bearer_scheme = HTTPBearer()


async def depends_jwt_bearer_auth(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    settings: Settings = Depends(AppState.depends_settings),
) -> typing.Dict[typing.Text, typing.Any]:
    """
    Get user info from JWT Bearer Token
    """

    token = credentials.credentials
    try:
        payload = verify_jwt_token(
            token,
            jwt_secret=settings.JWT_SECRET_KEY.get_secret_value(),
            jwt_algorithm=settings.JWT_ALGORITHM,
        )
        # 可能回傳 payload 或 user_id
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
