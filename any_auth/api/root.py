import typing

import fastapi
import pydantic

import any_auth.deps.app_state


class HealthResponse(pydantic.BaseModel):
    status: typing.Text


router = fastapi.APIRouter()


@router.get("/")
async def root():
    return {"message": "Hello World"}


@router.get("/health")
async def health(
    status: typing.Text = fastapi.Depends(any_auth.deps.app_state.depends_status),
) -> HealthResponse:
    return HealthResponse(status=status)
