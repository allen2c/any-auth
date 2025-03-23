# Relationship Map

This diagram shows the relationships between the main entities in Any Auth.

```mermaid
erDiagram
    %% Main entities with styling
    User {
        string id PK
        string username
        string email
        string hashed_password
        boolean email_verified
        boolean disabled
        json metadata
    }

    Organization {
        string id PK
        string name
        string full_name
        boolean disabled
        json metadata
    }

    Project {
        string id PK
        string organization_id FK
        string name
        string full_name
        boolean disabled
        string created_by FK
        json metadata
    }

    Role {
        string id PK
        string name
        array permissions
        string parent_id FK
        boolean disabled
    }

    %% Relationship entities
    OrganizationMember {
        string id PK
        string organization_id FK
        string user_id FK
        json metadata
    }

    ProjectMember {
        string id PK
        string project_id FK
        string user_id FK
        json metadata
    }

    RoleAssignment {
        string id PK
        string target_id FK
        string role_id FK
        string resource_id FK
    }

    APIKey {
        string id PK
        string resource_id FK
        string name
        string hashed_key
        string created_by FK
    }

    Invite {
        string id PK
        string resource_id FK
        string email
        string invited_by FK
        string temporary_token
    }

    %% Core entity relationships
    User ||--o{ OrganizationMember : "belongs to"
    User ||--o{ ProjectMember : "belongs to"
    User ||--o{ RoleAssignment : "has"
    User ||--o{ APIKey : "creates"
    User ||--o{ Invite : "creates"

    Organization ||--o{ OrganizationMember : "contains"
    Organization ||--o{ Project : "owns"

    Project ||--o{ ProjectMember : "contains"
    Project ||--o{ APIKey : "has"
    Project }o--|| Organization : "belongs to"

    %% Role structure
    Role }o--o| Role : "inherits from"
    Role ||--o{ RoleAssignment : "referenced by"

    %% Resource assignments
    RoleAssignment }o--|| User : "user target"
    RoleAssignment }o--|| APIKey : "API key target"

    %% Membership relationships
    OrganizationMember }o--|| Organization : "in"
    OrganizationMember }o--|| User : "is"

    ProjectMember }o--|| Project : "in"
    ProjectMember }o--|| User : "is"

    %% Invitations
    Invite }o--|| User : "for"
```

## Key Entities

- **User**: The core identity entity representing a user with authentication credentials
- **Organization**: Top-level tenant grouping entity for multi-tenant applications
- **Project**: Container for resources that can belong to an organization
- **Role**: Collection of permissions defining access levels in the system
- **RoleAssignment**: Maps a target (User or APIKey) to a Role for a specific resource
- **OrganizationMember**: Associates a User with an Organization
- **ProjectMember**: Associates a User with a Project
- **APIKey**: Alternative authentication method for programmatic access
- **Invite**: Mechanism for inviting users to join organizations or projects

## Important Notes

- **Resource Context**: RoleAssignment.resource_id can refer to:
    - The platform itself (using the constant "platform")
    - An Organization.id
    - A Project.id

- **Role Hierarchy**: Roles support inheritance through parent_id, allowing for
  permission inheritance and role specialization

- **Multi-tenant Design**: The system supports multi-tenant architecture through
  the Organization → Project hierarchy

- **Flexible Authentication**: Both Users and API Keys can be assigned roles,
  enabling both human and programmatic access with proper authorization

- **Resource Ownership**: Projects can optionally belong to Organizations,
  supporting both standalone and organization-contextualized projects
