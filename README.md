# Any Auth

**Essential Authentication Library for FastAPI Applications.**

Any Auth is a production-ready, MIT-licensed open-source library designed to streamline authentication and authorization in your FastAPI projects. It offers built-in support for JWT, OAuth 2.0 (Google), and flexible role-based access control, simplifying security for single-tenant or multi-tenant applications.

---

## Table of Contents

* [Overview](#overview)
* [Features](#features)
* [Installation](#installation)
* [Configuration](#configuration)
* [Usage](#usage)
    * [Running the App](#running-the-app)
    * [API Endpoints](#api-endpoints)
* [Development & Testing](#development--testing)
* [Contributing](#contributing)
* [License](#license)

---

## Overview

**Focus on building your application, not authentication.**

Any Auth provides the tools to:

* **Secure APIs:** Implement JWT-based authentication for your FastAPI endpoints.
* **Social Login:** Integrate Google OAuth for seamless user sign-in.
* **Manage Users:** Utilize a built-in user model with essential functionalities.
* **Control Access:** Implement role-based access control (RBAC) across organizations and projects.
* **Scale Easily:** Support multi-tenant applications with organizations and projects.
* **Choose your Backend:**  Leverage MongoDB with optional caching via Redis or DiskCache.

## Features

* **JWT Authentication:** Generate, verify, and refresh JWT tokens with customizable expiration.
* **Google OAuth 2.0:**  Simple integration for Google login, including automatic user account creation.
* **User Management:** Comprehensive user lifecycle management (create, update, retrieve, disable, enable).
* **Role-Based Access Control (RBAC):** Hierarchical roles (platform, organization, project) for fine-grained access control.
* **Organization & Project Management:** Built-in models for managing organizations and projects in multi-tenant scenarios.
* **Membership Management:**  Define and manage user memberships within organizations and projects.
* **Flexible Backend:**  Supports MongoDB as primary storage with optional Redis or DiskCache caching.
* **RESTful API:**  Complete API endpoints for authentication, user, role, organization, project, and role assignment management.
* **Testable:**  Extensive test suite using pytest and FastAPI's TestClient.

## Installation

Install Any Auth using Poetry:

```bash
# Clone the repository
git clone https://github.com/allen2c/any-auth.git
cd any-auth

# Install dependencies
poetry install
```

Or, if published on PyPI:

```bash
pip install any-auth # Replace with actual package name if different
```

## Configuration

Any Auth is configured via environment variables and a Pydantic `Settings` class. Key configurations include:

* **Database:** `DATABASE_URL` (MongoDB connection string).
* **JWT:** `JWT_SECRET_KEY` (secret key for JWT signing), `JWT_ALGORITHM` (default: HS256).
* **Token Expiration:** `TOKEN_EXPIRATION_TIME` (access token lifetime in seconds), `REFRESH_TOKEN_EXPIRATION_TIME` (refresh token lifetime in seconds).
* **Google OAuth (Optional):** `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`.
* **SMTP (Optional):**  `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM` (for password reset and notifications).

Example `.env` file:

```dotenv
DATABASE_URL=mongodb://localhost:27017
JWT_SECRET_KEY=your-very-secure-key
TOKEN_EXPIRATION_TIME=900
REFRESH_TOKEN_EXPIRATION_TIME=604800
```

## Usage

### Running the App

1. **Create your FastAPI app** in `any_auth/app.py` (example):

    ```python
    from any_auth.build_app import build_app
    from any_auth.config import Settings

    Settings.probe_required_environment_variables()
    app_settings = Settings()
    app = build_app(settings=app_settings)

    if __name__ == "__main__":
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
    ```

2. **Run the application:**

    ```bash
    uvicorn any_auth.app:app --reload
    ```

### API Endpoints

Explore the auto-generated API documentation at `/docs` or `/redoc` of your running application.

Key endpoint categories:

* **Authentication:** `/token` (login), `/logout`, `/refresh-token`, `/reset-password`, `/auth/google/login`.
* **User Management:** `/users` (create, list, get, update, disable/enable).
* **Organization Management:** `/organizations` (create, list, get, update, disable/enable), `/organizations/{organization_id}/projects`, `/organizations/{organization_id}/members`.
* **Project Management:** `/organizations/{organization_id}/projects`, `/projects` (create, list, get, update, disable/enable), `/projects/{project_id}/members`, `/projects/{project_id}/api-keys`.
* **Role & Role Assignment Management:** `/roles` (create, list, get, update, disable/enable), `/role-assignments`.

All endpoints are secured with role-based access control.

## Development & Testing

Run tests using pytest:

```bash
poetry run pytest
```

For development with live reload:

```bash
uvicorn any_auth.app:app --reload
```

## Contributing

Contributions are welcome!

1. Fork the repository.
2. Create a feature branch.
3. Write tests for your changes.
4. Ensure all tests pass.
5. Submit a pull request.

## License

[MIT License](LICENSE)

Copyright (c) 2025 AllenChou
