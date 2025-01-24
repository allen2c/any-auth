import typing

import pydantic


class TokenUserInfo(pydantic.BaseModel):
    sub: typing.Text = pydantic.Field(default="")
    name: typing.Text = pydantic.Field(default="")
    given_name: typing.Text = pydantic.Field(default="")
    family_name: typing.Text = pydantic.Field(default="")
    middle_name: typing.Text = pydantic.Field(default="")
    nickname: typing.Text = pydantic.Field(default="")
    preferred_username: typing.Text = pydantic.Field(default="")
    profile: typing.Text = pydantic.Field(default="")
    picture: typing.Text = pydantic.Field(default="")
    website: typing.Text = pydantic.Field(default="")
    email: typing.Text = pydantic.Field(default="")
    email_verified: bool = pydantic.Field(default=False)
    gender: typing.Text = pydantic.Field(default="")
    birthdate: typing.Text = pydantic.Field(default="")
    zoneinfo: typing.Text = pydantic.Field(default="")
    locale: typing.Text = pydantic.Field(default="")
    phone_number: typing.Text = pydantic.Field(default="")
    phone_number_verified: bool = pydantic.Field(default=False)
    address: typing.Text = pydantic.Field(default="")
    updated_at: int = pydantic.Field(default=0)
    iss: typing.Text = pydantic.Field(default="")
    azp: typing.Text = pydantic.Field(default="")
    aud: typing.Text = pydantic.Field(default="")
    at_hash: typing.Text = pydantic.Field(default="")
    nonce: typing.Text = pydantic.Field(default="")
    iat: int = pydantic.Field(default=0)
    exp: int = pydantic.Field(default=0)


class SessionStateGoogleData(pydantic.BaseModel):
    session_state: typing.Text
    data: typing.Dict[typing.Text, typing.Any]
    exp: float

    @classmethod
    def from_session(
        cls, session: typing.Dict[typing.Text, typing.Any]
    ) -> "SessionStateGoogleData":
        for key, value in session.items():
            if key.startswith("_state_google_"):
                return cls.model_validate(
                    {
                        "session_state": key,
                        "data": value["data"],
                        "exp": value["exp"],
                    }
                )
        raise ValueError("No Google session data found")


class GoogleToken(pydantic.BaseModel):
    access_token: pydantic.SecretStr
    expires_in: int
    scope: typing.Text
    token_type: typing.Text
    id_token: pydantic.SecretStr
    expires_at: int
    userinfo: TokenUserInfo


if __name__ == "__main__":
    session = {
        "_state_google_ggwp1234": {
            "data": {
                "redirect_uri": "http://localhost:8000/auth/google/callback",
                "nonce": "REDACTED_NONCE",
                "url": "https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=REDACTED_CLIENT_ID&redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fauth%2Fgoogle%2Fcallback&scope=openid+email+profile&state=REDACTED_STATE&nonce=REDACTED_NONCE",  # noqa: E501
            },
            "exp": 1737687436.542845,
        }
    }

    token = {
        "access_token": "REDACTED_ACCESS_TOKEN",
        "expires_in": 3598,
        "scope": "https://www.googleapis.com/auth/userinfo.email openid https://www.googleapis.com/auth/userinfo.profile",  # noqa: E501
        "token_type": "Bearer",
        "id_token": "REDACTED_ID_TOKEN",
        "expires_at": 1737687437,
        "userinfo": {
            "iss": "https://accounts.google.com",
            "azp": "REDACTED_CLIENT_ID",
            "aud": "REDACTED_CLIENT_ID",
            "sub": "REDACTED_SUB",
            "email": "REDACTED_EMAIL",
            "email_verified": True,
            "at_hash": "REDACTED_AT_HASH",
            "nonce": "REDACTED_NONCE",
            "name": "REDACTED_NAME",
            "picture": "REDACTED_PICTURE_URL",
            "given_name": "REDACTED_GIVEN_NAME",
            "iat": 1737683839,
            "exp": 1737687439,
        },
    }

    print(SessionStateGoogleData.from_session(session))
    print(GoogleToken.model_validate(token))
