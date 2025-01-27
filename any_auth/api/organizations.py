import asyncio
import typing

import fastapi

import any_auth.deps.app_state as AppState
import any_auth.deps.permission
from any_auth.backend import BackendClient
from any_auth.deps.auth import depends_active_user
from any_auth.types.organization import (
    Organization,
    OrganizationCreate,
    OrganizationUpdate,
)
from any_auth.types.organization_member import (
    OrganizationMember,
    OrganizationMemberCreate,
)
from any_auth.types.pagination import Page
from any_auth.types.role import Permission, Role
from any_auth.types.user import UserInDB

router = fastapi.APIRouter()


@router.get("/organizations", tags=["Organizations"])
async def api_list_organizations(
    limit: int = fastapi.Query(default=20, ge=1, le=100),
    order: typing.Literal["asc", "desc"] = fastapi.Query(default="desc"),
    after: typing.Text = fastapi.Query(default=""),
    before: typing.Text = fastapi.Query(default=""),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.ORG_LIST, from_="organization"
        )
    ),
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
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.ORG_CREATE, from_="organization"
        )
    ),
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
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.ORG_GET, from_="organization"
        )
    ),
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
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.ORG_UPDATE, from_="organization"
        )
    ),
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
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.ORG_DELETE, from_="organization"
        )
    ),
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
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.ORG_DISABLE, from_="organization"
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    await asyncio.to_thread(
        backend_client.organizations.set_disabled, organization_id, disabled=False
    )

    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)


@router.get("/organizations/{organization_id}/members", tags=["Organizations"])
async def api_list_organization_members(
    organization_id: typing.Text = fastapi.Path(
        ..., description="The ID of the organization to retrieve members for"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.ORG_MEMBER_LIST, from_="organization"
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Page[OrganizationMember]:
    org_members = await asyncio.to_thread(
        backend_client.organization_members.retrieve_by_organization_id,
        organization_id,
    )
    return Page[OrganizationMember].model_validate(
        {
            "object": "list",
            "data": org_members,
            "first_id": org_members[0].id if org_members else None,
            "last_id": org_members[-1].id if org_members else None,
            "has_more": False,
        }
    )


@router.post("/organizations/{organization_id}/members", tags=["Organizations"])
async def api_create_organization_member(
    organization_id: typing.Text = fastapi.Path(
        ..., description="The ID of the organization to create a member for"
    ),
    member_create: OrganizationMemberCreate = fastapi.Body(
        ..., description="The member to create"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.ORG_MEMBER_CREATE, from_="organization"
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> OrganizationMember:
    member = await asyncio.to_thread(
        backend_client.organization_members.create,
        member_create=member_create,
        organization_id=organization_id,
    )
    return member


@router.get(
    "/organizations/{organization_id}/members/{member_id}", tags=["Organizations"]
)
async def api_retrieve_organization_member(
    organization_id: typing.Text = fastapi.Path(
        ..., description="The ID of the organization to retrieve a member for"
    ),
    member_id: typing.Text = fastapi.Path(
        ..., description="The ID of the member to retrieve"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.ORG_MEMBER_GET, from_="organization"
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> OrganizationMember:
    member = await asyncio.to_thread(
        backend_client.organization_members.retrieve,
        member_id,
    )
    if not member:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )
    return member


@router.delete(
    "/organizations/{organization_id}/members/{member_id}", tags=["Organizations"]
)
async def api_delete_organization_member(
    organization_id: typing.Text = fastapi.Path(
        ..., description="The ID of the organization to delete a member for"
    ),
    member_id: typing.Text = fastapi.Path(
        ..., description="The ID of the member to delete"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.ORG_MEMBER_DELETE, from_="organization"
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    await asyncio.to_thread(
        backend_client.organization_members.delete,
        member_id,
    )
    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)
