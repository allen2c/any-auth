import logging
import typing

import fastapi
import pydantic

import any_auth.deps.app_state as AppState

logger = logging.getLogger(__name__)


class HealthResponse(pydantic.BaseModel):
    status: typing.Text


router = fastapi.APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(
    status: typing.Literal["ok", "error", "starting"] | typing.Text = fastapi.Depends(
        AppState.depends_status
    ),
) -> HealthResponse:
    """Application health status endpoint."""

    if status == "starting":
        raise fastapi.HTTPException(status_code=503, detail="Server is starting")

    elif status == "error":
        raise fastapi.HTTPException(status_code=500, detail="Server is in error state")

    elif status == "ok":
        return HealthResponse(status=status)

    else:
        raise fastapi.HTTPException(status_code=500, detail="Unknown server state")
