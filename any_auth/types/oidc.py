import typing

import pydantic


class JWK(pydantic.BaseModel):
    n: str
    e: str
    kty: str
    kid: str
    use: str
    alg: str


class JWKSet(pydantic.BaseModel):
    keys: typing.List[JWK]


class OpenIDConfiguration(pydantic.BaseModel):
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    response_types_supported: typing.List[str] = pydantic.Field(default_factory=list)
    subject_types_supported: typing.List[str] = pydantic.Field(default_factory=list)
    id_token_signing_alg_values_supported: typing.List[str] = pydantic.Field(
        default_factory=list
    )
    userinfo_endpoint: typing.Optional[str] = pydantic.Field(default=None)
    token_endpoint_auth_signing_alg_values_supported: typing.Optional[
        typing.List[str]
    ] = pydantic.Field(default=None)
    scopes_supported: typing.List[str] = pydantic.Field(default_factory=list)
    token_endpoint_auth_methods_supported: typing.List[str] = pydantic.Field(
        default_factory=list
    )
    claims_supported: typing.List[str] = pydantic.Field(default_factory=list)
    grant_types_supported: typing.List[str] = pydantic.Field(default_factory=list)
    service_documentation: typing.Optional[str] = pydantic.Field(default=None)
    revocation_endpoint: typing.Optional[str] = pydantic.Field(default=None)
    introspection_endpoint: typing.Optional[str] = pydantic.Field(default=None)
