import asyncio
import typing

import fastapi

import any_auth.deps.app_state as AppState
from any_auth.backend import BackendClient
from any_auth.deps.auth import depends_active_user
from any_auth.types.organization import (
    Organization,
    OrganizationCreate,
    OrganizationUpdate,
)
from any_auth.types.pagination import Page
from any_auth.types.user import UserInDB

router = fastapi.APIRouter()


@router.get("/organizations", tags=["Organizations"])
async def api_list_organizations(
    limit: int = fastapi.Query(default=20, ge=1, le=100),
    order: typing.Literal["asc", "desc"] = fastapi.Query(default="desc"),
    after: typing.Text = fastapi.Query(default=""),
    before: typing.Text = fastapi.Query(default=""),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Page[Organization]:
    page_organizations = await asyncio.to_thread(
        backend_client.organizations.list,
        limit=limit,
        order=order,
        after=after.strip() or None,
        before=before.strip() or None,
    )
    return Page[Organization].model_validate(page_organizations.model_dump())


@router.post("/organizations", tags=["Organizations"])
async def api_create_organization(
    org_create: OrganizationCreate = fastapi.Body(
        ..., description="The organization to create"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Organization:
    org = await asyncio.to_thread(
        backend_client.organizations.create,
        org_create,
    )
    return Organization.model_validate(org.model_dump())


@router.get("/organizations/{organization_id}", tags=["Organizations"])
async def api_retrieve_organization(
    organization_id: typing.Text = fastapi.Path(
        ..., description="The ID of the organization to retrieve"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Organization:
    organization_id = organization_id.strip()

    if not organization_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Organization ID is required",
        )

    org = await asyncio.to_thread(
        backend_client.organizations.retrieve, organization_id
    )

    if not org:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    return Organization.model_validate(org.model_dump())


@router.post("/organizations/{organization_id}", tags=["Organizations"])
async def api_update_organization(
    organization_id: typing.Text = fastapi.Path(
        ..., description="The ID of the organization to update"
    ),
    org_update: OrganizationUpdate = fastapi.Body(
        ..., description="The organization to update"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Organization:
    organization_id = organization_id.strip()

    if not organization_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Organization ID is required",
        )

    org = await asyncio.to_thread(
        backend_client.organizations.update,
        organization_id,
        org_update,
    )
    return Organization.model_validate(org.model_dump())


@router.delete("/organizations/{organization_id}", tags=["Organizations"])
async def api_delete_organization(
    organization_id: typing.Text = fastapi.Path(
        ..., description="The ID of the organization to delete"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    await asyncio.to_thread(
        backend_client.organizations.set_disabled, organization_id, disabled=True
    )
    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)


@router.post("/organizations/{organization_id}/enable", tags=["Organizations"])
async def api_enable_organization(
    organization_id: typing.Text = fastapi.Path(
        ..., description="The ID of the organization to enable"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    await asyncio.to_thread(
        backend_client.organizations.set_disabled, organization_id, disabled=False
    )

    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)
