import typing

import fastapi
import pydantic


class HealthResponse(pydantic.BaseModel):
    status: typing.Literal["ok", "error", "starting"]


router = fastapi.APIRouter()


@router.get("/")
async def root():
    return {"message": "Hello World"}


@router.get("/health")
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
