# AnyAuth Schemas

This document provides an overview of the core data schemas (Pydantic models) used within the AnyAuth library. These schemas define the structure of data for users, organizations, projects, authentication, authorization, and related entities.

For a visual representation of how these schemas relate to each other, see the [Relationship Map][relationship_map.md].

## Core Entities

* **User (`any_auth.types.user`)**: Represents a user account, including profile information, credentials (hashed password stored separately in `UserInDB`), verification status, and metadata. Includes `UserCreate` for registration and `UserUpdate` for modifications.
* **Organization (`any_auth.types.organization`)**: Defines a top-level tenant or grouping, with details like name, full name, status, and metadata. Includes `OrganizationCreate` and `OrganizationUpdate` models.
* **Project (`any_auth.types.project`)**: Represents a project, potentially belonging to an organization, containing name, status, creator info, and metadata. Includes `ProjectCreate` and `ProjectUpdate` models.

## Membership & Relationships

* **OrganizationMember (`any_auth.types.organization_member`)**: Links a `User` to an `Organization`, tracking join time and metadata. Includes `OrganizationMemberCreate`.
* **ProjectMember (`any_auth.types.project_member`)**: Links a `User` to a `Project`, tracking join time and metadata. Includes `ProjectMemberCreate`.

## Authorization & Roles

* **Role (`any_auth.types.role`)**: Defines a set of permissions. Roles can have descriptions, parent roles (for inheritance), and a disabled status. Includes `RoleCreate` and `RoleUpdate` models. Predefined roles are available (e.g., `PlatformManager`, `OrganizationOwner`, `ProjectViewer`).
* **Permission (`any_auth.types.role`)**: An `enum.StrEnum` defining specific actions allowed within the system (e.g., `user.create`, `project.update`, `iam.setPolicy`).
* **RoleAssignment (`any_auth.types.role_assignment`)**: Connects a target (User ID or API Key ID) to a `Role` for a specific resource (Platform, Organization ID, or Project ID). Includes `RoleAssignmentCreate`.

## Authentication & Security

* **APIKey (`any_auth.types.api_key`)**: Represents an API key for programmatic access, linked to a resource and creator. `APIKeyInDB` includes secure storage details [prefix, salt, hashed key]. Includes `APIKeyCreate` and `APIKeyUpdate` models.
* **OAuthClient (`any_auth.types.oauth_client`)**: Defines an OAuth 2.0 client application (public or confidential) with its allowed grant types, response types, redirect URIs, scopes, and PKCE settings. Includes `OAuthClientCreate`.
* **AuthorizationCode (`any_auth.types.oauth2`)**: Temporary code issued during the OAuth 2.0 authorization code flow, linked to user, client, scope, and includes PKCE details if used.
* **OAuth2Token (`any_auth.types.oauth2`)**: Represents issued access and refresh tokens, including scope, expiration, user/client linkage, and revocation status.
* **ID Token Claims (`any_auth.utils.id_token`)**: While not a direct schema file, this utility generates claims for OpenID Connect ID Tokens based on requested scopes (e.g., `profile`, `email`).
* **TokenRequest/Response (`any_auth.types.oauth2`)**: Models for standard OAuth 2.0 token endpoint requests and responses.
* **TokenIntrospectionResponse (`any_auth.types.oauth2`)**: Schema for the response from the OAuth 2.0 token introspection endpoint (RFC 7662).

## Utility Schemas

* **Invite (`any_auth.types.invite`)**: Represents an invitation for a user (email) to join a specific resource, including expiration and a temporary token. Includes `InviteCreate`.
* **Page (`any_auth.types.pagination`)**: Generic schema for paginated list responses, containing the list of data items, IDs for cursor-based pagination, and a flag indicating if more items are available.
* **Settings (`any_auth.config`)**: Defines application configuration loaded from environment variables, including database/cache URLs, JWT secrets, token lifetimes, Google OAuth credentials, and SMTP settings.
* **BackendSettings (`any_auth.backend.settings`)**: Configures database collection names and index definitions.

This index provides a high-level map. Refer to the specific files within `any_auth/types/` and `any_auth/backend/` for detailed field definitions and validation rules.

[relationship_map.md]: relationship_map.md
