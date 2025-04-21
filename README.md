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

## OAuth 2.0 Specifications

Any-Auth implements authentication following these specifications:

* **RFC 6749:** The core specification defining the **OAuth 2.0 authorization framework**.
* **RFC 7519:** Defines the structure and processing rules for **JSON Web Tokens (JWT)**.
* **RFC 9068:** Specifies a profile for using **JWTs as OAuth 2.0 Access Tokens**.
* **RFC 8707:** Defines a mechanism for clients to indicate the intended **resource server(s)** during authorization requests (Resource Indicators).
* **RFC 7518:** Defines **cryptographic algorithms** and identifiers used with JSON Web Signatures (JWS), Encryption (JWE), and Keys (JWK) (JSON Web Algorithms - JWA).
* **RFC 7517:** Defines the **JSON Web Key (JWK)** format for representing cryptographic keys.
* **RFC 8141:** Defines the syntax and rules for **Uniform Resource Names (URNs)**. (Often used for identifiers within security contexts).
* **RFC 7662:** Specifies an endpoint for validating and retrieving metadata about OAuth 2.0 tokens (**Token Introspection**).
* **RFC 6750:** Defines how to use **Bearer Tokens** to access OAuth 2.0 protected resources.

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
