# Any Auth

A comprehensive, production‐ready authentication and authorization library for FastAPI applications. **Any Auth** provides built-in support for JWT-based authentication, OAuth 2.0 (including Google login), and role-based access control with flexible organization and project membership management.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
    - [Building and Running the App](#building-and-running-the-app)
    - [API Endpoints](#api-endpoints)
- [Development and Testing](#development-and-testing)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

**Any Auth** is an MIT‑licensed open source library designed to simplify and standardize the implementation of authentication and authorization in FastAPI projects. Whether you are building a single‑tenant or multi‑tenant application, Any Auth gives you the tools to:

- Secure your endpoints using JWT tokens.
- Integrate third‑party authentication (e.g. Google OAuth).
- Manage users with a built‑in user model.
- Implement role‑based access control (RBAC) across organizations and projects.
- Easily extend or integrate with your own backend database (MongoDB, Redis, or DiskCache).

---

## Features

- **JWT Authentication:** Issue, verify, and refresh JWT tokens with configurable expiration times.
- **OAuth Integration:** Seamless Google OAuth2 integration with automatic user creation.
- **User Management:** Create, update, retrieve, disable, and enable users.
- **Role-Based Access Control:** Pre‑defined roles (platform, organization, project) with a hierarchical role model.
- **Organization & Project Management:** Support for multi‑tenant scenarios with organizations and projects.
- **Membership & Role Assignments:** Manage organization and project memberships and assign roles to users.
- **Extensible Backend:** Use MongoDB as the primary store with optional caching via Redis or DiskCache.
- **RESTful API Endpoints:** A complete set of endpoints for authentication, user, role, organization, project, and role assignment management.
- **Testing Ready:** Comes with an extensive test suite using pytest and FastAPI’s TestClient.

---

## Installation

You can install **Any Auth** via pip (if published) or use it as a sub‑module in your project. To install from source, clone the repository and install the dependencies using [Poetry](https://python-poetry.org/) or pip.

### Using Poetry

```bash
# Clone the repository
git clone https://github.com/yourusername/any-auth.git
cd any-auth

# Install dependencies and dev dependencies
poetry install

# To run tests:
poetry run pytest
```

### Using pip

If you publish on PyPI, installation might be as simple as:

```bash
pip install any-auth
```

(Replace the above command with the actual package name if different.)

---

## Configuration

Any Auth is configured using environment variables and a settings class (based on Pydantic). The key configuration options include:

- **DATABASE_URL:** The URL for your MongoDB instance.
- **JWT_SECRET_KEY:** A secure key used for signing JWT tokens.
- **JWT_ALGORITHM:** The JWT algorithm (e.g. HS256).
- **TOKEN_EXPIRATION_TIME:** Lifetime (in seconds) for access tokens.
- **REFRESH_TOKEN_EXPIRATION_TIME:** Lifetime (in seconds) for refresh tokens.
- **OAuth Settings:** (Optional) `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` for Google OAuth.
- **SMTP Settings:** (Optional) Configure SMTP server details for password reset and notification emails.

You can set these variables in your environment or in a `.env` file. For example:

```dotenv
DATABASE_URL=mongodb://localhost:27017
JWT_SECRET_KEY=your-very-secure-key
JWT_ALGORITHM=HS256
TOKEN_EXPIRATION_TIME=900        # 15 minutes
REFRESH_TOKEN_EXPIRATION_TIME=604800  # 7 days
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your-smtp-username
SMTP_PASSWORD=your-smtp-password
```

---

## Usage

### Building and Running the App

Any Auth is built on top of FastAPI. To create and run your application:

1. **Create a Settings instance and build the app:**

   ```python
   # any_auth/app.py
   from any_auth.build_app import build_app
   from any_auth.config import Settings

   Settings.probe_required_environment_variables()

   app_settings = Settings()  # Loads configuration from env/.env
   app = build_app(settings=app_settings)

   if __name__ == "__main__":
       import uvicorn
       uvicorn.run(app, host="0.0.0.0", port=8000)
   ```

2. **Run the App:**

   ```bash
   uvicorn any_auth.app:app --reload
   ```

### API Endpoints

Any Auth exposes a RESTful API for the following functionalities:

- **Authentication:**
    - `POST /token` – Obtain JWT tokens by providing username/email and password.
    - `POST /logout` – Invalidate a token.
    - `POST /refresh-token` – Refresh an expired token.
    - `POST /reset-password` and `POST /request-reset-password` – Password reset flow.
    - `GET /auth/google/login` and `GET /auth/google/callback` – Google OAuth endpoints.

- **User Management:**
    - `GET /users` – List users.
    - `POST /users` – Create a new user.
    - `GET /users/{user_id}` – Retrieve a user’s details.
    - `POST /users/{user_id}` – Update user information.
    - `DELETE /users/{user_id}` – Disable a user.
    - `POST /users/{user_id}/enable` – Enable a disabled user.
    - Additional endpoints for role assignments and listing user organizations/projects.

- **Organization and Project Management:**
    - `GET /organizations` and `GET /organizations/{organization_id}` – List and retrieve organizations.
    - `POST /organizations` – Create an organization.
    - `POST /organizations/{organization_id}` – Update an organization.
    - `DELETE /organizations/{organization_id}` and `POST /organizations/{organization_id}/enable` – Disable/enable organizations.
    - Similar endpoints exist for projects under an organization:
        - `GET /organizations/{organization_id}/projects`
        - `POST /organizations/{organization_id}/projects`
        - `GET /organizations/{organization_id}/projects/{project_id}`
        - `POST /organizations/{organization_id}/projects/{project_id}` (update)
        - `DELETE /organizations/{organization_id}/projects/{project_id}` and `POST /organizations/{organization_id}/projects/{project_id}/enable`

- **Role and Role Assignment Management:**
    - `GET /roles` – List roles.
    - `POST /roles` – Create a role.
    - `GET /roles/{role_id}` – Retrieve a role.
    - `POST /roles/{role_id}` – Update a role.
    - `DELETE /roles/{role_id}` and `POST /roles/{role_id}/enable` – Disable/enable roles.
    - Endpoints to create, retrieve, and delete role assignments (for organizations, projects, etc.).

- **Console Endpoints (Frontend for Admins):**
    - Endpoints under `/c/` provide a basic web interface for login, viewing user profiles, and dashboards.

All endpoints are secured using appropriate permissions and roles. For detailed API documentation, you can use FastAPI’s auto‑generated docs by navigating to `/docs` or `/redoc` in your running application.

---

## Development and Testing

The project comes with a comprehensive test suite using pytest. To run all tests, use:

```bash
pytest
```

The tests cover backend database operations (using MongoDB), API endpoint access control, role assignments, and more. We use fixtures to set up test databases and sessions so that tests can run isolated from production data.

For development, you can use [uvicorn](https://www.uvicorn.org/) to run the app with live reload:

```bash
uvicorn any_auth.app:app --reload
```

---

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Write tests for your changes.
4. Ensure all tests pass.
5. Submit a pull request describing your changes.

Feel free to open issues or discussions if you have ideas or questions.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
