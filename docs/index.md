# Any-Auth

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) **Essential Authentication Library for FastAPI Applications.**

Any Auth streamlines authentication and authorization for FastAPI projects. It provides built-in support for JWT, Google OAuth 2.0, and flexible role-based access control (RBAC) for single or multi-tenant applications.

## Features

* **JWT Authentication:** Generate, verify, and refresh tokens.
* **Google OAuth 2.0:** Simple integration for Google login.
* **User Management:** Create, update, retrieve, and disable/enable users.
* **RBAC:** Hierarchical roles (platform, organization, project) for access control.
* **Multi-Tenancy:** Built-in models for organizations and projects.
* **Flexible Backend:** Supports MongoDB with optional Redis or DiskCache caching.
* **API Endpoints:** RESTful API for managing auth, users, roles, organizations, and projects.
* **Testing:** Includes a comprehensive test suite using pytest.

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
* `JWT_SECRET_KEY`: Secret key for signing JWTs.
* `TOKEN_EXPIRATION_TIME`: Access token lifetime [seconds].
* `REFRESH_TOKEN_EXPIRATION_TIME`: Refresh token lifetime [seconds].
* `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`: (Optional) For Google OAuth.
* SMTP variables: (Optional) For email features like password reset.

Refer to `any_auth/config.py` for all settings.

## Quick Start

1. **Setup FastAPI App:**
    Create your app file (e.g., `main.py`):

    ```python
    from any_auth.build_app import build_app
    from any_auth.config import Settings

    Settings.probe_required_environment_variables()
    app_settings = Settings()
    app = build_app(settings=app_settings)

    # Optional: Add custom routes or middleware here

    if __name__ == "__main__":
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
    ```

2. **Run the Application:**

    ```bash
    uvicorn main:app --reload
    ```

3. **Explore API:**
    Access the auto-generated API documentation at `/docs` or `/redoc`.

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
4. Ensure all tests pass.
5. Submit a pull request.

## License

[MIT License](https://www.google.com/search?q=LICENSE)

Copyright (c) 2025 AllenChou
