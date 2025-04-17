"""
OAuth 2.0 scope registry for AnyAuth.
"""

import enum
import typing

from any_auth.types.role import Permission


class StandardScope(str, enum.Enum):
    """
    Standard OAuth 2.0 scopes.
    """

    # OpenID Connect scopes
    OPENID = "openid"
    PROFILE = "profile"
    EMAIL = "email"
    ADDRESS = "address"
    PHONE = "phone"

    # API access
    API = "api"

    # User management
    USER_READ = "user:read"
    USER_WRITE = "user:write"

    # Organization management
    ORGANIZATION_READ = "organization:read"
    ORGANIZATION_WRITE = "organization:write"

    # Project management
    PROJECT_READ = "project:read"
    PROJECT_WRITE = "project:write"

    # Offline access (for refresh tokens)
    OFFLINE_ACCESS = "offline_access"


# Maps OAuth 2.0 scopes to AnyAuth permissions
SCOPE_TO_PERMISSIONS: typing.Dict[str, typing.List[Permission]] = {
    # User scopes
    StandardScope.USER_READ: [
        Permission.USER_GET,
        Permission.USER_LIST,
    ],
    StandardScope.USER_WRITE: [
        Permission.USER_CREATE,
        Permission.USER_UPDATE,
        Permission.USER_DELETE,
        Permission.USER_DISABLE,
        Permission.USER_INVITE,
    ],
    # Organization scopes
    StandardScope.ORGANIZATION_READ: [
        Permission.ORG_GET,
        Permission.ORG_LIST,
        Permission.ORG_MEMBER_LIST,
        Permission.ORG_MEMBER_GET,
    ],
    StandardScope.ORGANIZATION_WRITE: [
        Permission.ORG_CREATE,
        Permission.ORG_UPDATE,
        Permission.ORG_DELETE,
        Permission.ORG_DISABLE,
        Permission.ORG_MEMBER_CREATE,
        Permission.ORG_MEMBER_DELETE,
    ],
    # Project scopes
    StandardScope.PROJECT_READ: [
        Permission.PROJECT_GET,
        Permission.PROJECT_LIST,
        Permission.PROJECT_MEMBER_LIST,
        Permission.PROJECT_MEMBER_GET,
    ],
    StandardScope.PROJECT_WRITE: [
        Permission.PROJECT_CREATE,
        Permission.PROJECT_UPDATE,
        Permission.PROJECT_DELETE,
        Permission.PROJECT_DISABLE,
        Permission.PROJECT_MEMBER_CREATE,
        Permission.PROJECT_MEMBER_DELETE,
    ],
}


# Helper functions for scope handling
def scope_to_permissions(scope: str) -> typing.List[Permission]:
    """
    Convert an OAuth 2.0 scope to a list of AnyAuth permissions.

    Args:
        scope: A single OAuth 2.0 scope

    Returns:
        List of corresponding AnyAuth permissions
    """
    return SCOPE_TO_PERMISSIONS.get(scope, [])


def scopes_to_permissions(scopes: typing.List[str]) -> typing.List[Permission]:
    """
    Convert a list of OAuth 2.0 scopes to a list of AnyAuth permissions.

    Args:
        scopes: List of OAuth 2.0 scopes

    Returns:
        List of corresponding AnyAuth permissions
    """
    permissions = []
    for scope in scopes:
        permissions.extend(scope_to_permissions(scope))
    return list(set(permissions))  # Remove duplicates


def permissions_to_scopes(permissions: typing.List[Permission]) -> typing.List[str]:
    """
    Find the minimal set of scopes that would grant the given permissions.

    Args:
        permissions: List of AnyAuth permissions

    Returns:
        List of corresponding OAuth 2.0 scopes
    """
    permissions_set = set(permissions)
    scopes = []

    # Find scopes that would grant all the required permissions
    for scope, scope_permissions in SCOPE_TO_PERMISSIONS.items():
        if any(perm in permissions_set for perm in scope_permissions):
            scopes.append(scope)
            # Remove the granted permissions from the set
            permissions_set -= set(scope_permissions)

        # If we've covered all permissions, we're done
        if not permissions_set:
            break

    return scopes
