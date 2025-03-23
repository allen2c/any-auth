# Any Auth Documentation

Welcome to the Any Auth documentation. Any Auth is an essential authentication and authorization library for FastAPI applications.

## Overview

Any Auth provides a comprehensive solution for authentication and authorization in your FastAPI projects. It offers built-in support for JWT, OAuth 2.0 (Google), and role-based access control, making it easy to secure single-tenant or multi-tenant applications.

## Key Features

- **JWT Authentication**: Secure token-based authentication with refresh capabilities
- **OAuth Integration**: Built-in support for Google OAuth login
- **Role-Based Access Control**: Fine-grained permissions at platform, organization, and project levels
- **Multi-Tenant Architecture**: Support for organizations, projects, and hierarchical access control
- **API Key Management**: Create and manage API keys with customizable permissions
- **Invitation System**: Invite users to organizations and projects
- **Flexible Storage**: MongoDB backend with optional Redis or DiskCache caching

## Getting Started

### Installation

```bash
pip install any-auth
```

### Basic Configuration

```python
from any_auth.build_app import build_app
from any_auth.config import Settings

# Configure environment variables (see Configuration section)
Settings.probe_required_environment_variables()
app_settings = Settings()
app = build_app(settings=app_settings)
```

### Core Concepts

- **Users**: Authentication identities with credentials and profile information
- **Roles**: Sets of permissions defining what actions users can perform
- **Organizations**: Top-level tenant containers for multi-tenant applications
- **Projects**: Containers for resources that can belong to organizations
- **Role Assignments**: Connections between users/API keys and roles for specific resources

## API Reference

Any Auth provides a comprehensive REST API for authentication, user management, organization/project management, and role assignments. Explore the auto-generated API documentation at `/docs` when your application is running.

## Additional Resources

- [Schema Relationships](schemas/relationshep_map.md): Visual representation of data relationships
- [GitHub Repository](https://github.com/allen2c/any-auth): Source code and issue tracking

## License

Any Auth is available under the MIT License. See the LICENSE file for more information.
