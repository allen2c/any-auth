# Any-Auth

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) **Essential Authentication Library for FastAPI Applications.**

Any Auth streamlines authentication and authorization for FastAPI projects. It provides built-in support for JWT (using asymmetric keys by default), Google OAuth 2.0, and flexible role-based access control (RBAC) for single or multi-tenant applications.

## Features

* **JWT Authentication:** Generate, verify, and refresh tokens using algorithms like RS256 [default].
* **Google OAuth 2.0:** Simple integration for Google login.
* **User Management:** Create, update, retrieve, and disable/enable users. See `any_auth/types/user.py`.
* **RBAC:** Hierarchical roles (platform, organization, project) for access control. See `any_auth/types/role.py`.
* **Multi-Tenancy:** Built-in models for organizations and projects. See `any_auth/types/organization.py` and `any_auth/types/project.py`.
* **Flexible Backend:** Supports MongoDB with optional Redis or DiskCache caching.
* **API Endpoints:** RESTful API for managing auth, users, roles, organizations, and projects. See `any_auth/api/`.
* **Testing:** Includes a comprehensive test suite using pytest.
* **Security:** Includes middleware for security headers, CSRF protection, and rate limiting.

## OAuth 2.0 / OpenID Connect Support

Any-Auth implements authentication following key specifications, including:

* **OAuth 2.0 Framework (RFC 6749)**
* **JSON Web Token - JWT (RFC 7519)**
* **JWT Profile for OAuth 2.0 Access Tokens (RFC 9068)**
* **JSON Web Algorithms - JWA (RFC 7518)**
* **JSON Web Key - JWK (RFC 7517)**
* **Token Introspection (RFC 7662)**
* **Bearer Token Usage (RFC 6750)**
* **OpenID Connect Core** (including Discovery, UserInfo)

## Installation

```bash
# Clone the repository
git clone [https://github.com/allen2c/any-auth.git](https://github.com/allen2c/any-auth.git)
cd any-auth

# Install dependencies using Poetry
poetry install
````

## Configuration

Configure Any Auth using environment variables. Key settings include:

* `DATABASE_URL`: MongoDB connection string.
* `JWT_PRIVATE_KEY` / `JWT_PUBLIC_KEY`: Private/Public key content for signing JWTs [default algorithm: RS256]. Alternatively, use `JWT_PRIVATE_KEY_PATH` / `JWT_PUBLIC_KEY_PATH`.
* `TOKEN_EXPIRATION_TIME`: Access token lifetime [seconds].
* `REFRESH_TOKEN_EXPIRATION_TIME`: Refresh token lifetime [seconds].
* `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`: (Optional) For Google OAuth.
* SMTP variables (`SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_PORT`, `SMTP_SERVER`): (Optional) For email features like password reset.

Refer to `any_auth/config.py` for all settings.

## Quick Start

1. **Setup FastAPI App:**
    Ensure your environment variables are set. Create your app file (e.g., `main.py`):

    ```python
    # main.py
    from any_auth.app import app # app already builds using build_app and settings
    # Optional: Add custom routes or middleware here
    # app.include_router(...)

    if __name__ == "__main__":
        import uvicorn
        # Access app.settings if needed after initialization in any_auth.app
        uvicorn.run(app, host="0.0.0.0", port=8000)
    ```

2. **Run the Development Server:**
    Use the Makefile command for the development server with hot-reloading:

    ```bash
    make svc-dev
    ```

    Alternatively, run directly:

    ```bash
    fastapi dev any_auth/app.py
    ```

3. **Explore API:**
    Access the auto-generated API documentation (if not in production environment) at `/docs` or `/redoc`.

## Development

* **Install Dev Dependencies:** `poetry install --all-extras --all-groups`
* **Format Code:** `make format-all`
* **Run Tests:** `make pytest`
* **Run Dev Server:** `make svc-dev`
* **Build Docs:** `make mkdocs`

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository.
2. Create a feature branch.
3. Write tests for your changes.
4. Ensure all tests pass (`make pytest`).
5. Submit a pull request.

## License

[MIT License](https://www.google.com/search?q=LICENSE)

Copyright (c) 2025 AllenChou
