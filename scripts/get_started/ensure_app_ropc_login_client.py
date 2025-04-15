import requests

# From script 'scripts/get_started/ensure_app_platform_creator.py'
admin_username = "<PLATFORM_CREATOR_USERNAME>"
admin_password = "<PLATFORM_CREATOR_PASSWORD>"

response = requests.post(
    "http://localhost:8000/oauth2/token",
    data={
        "grant_type": "password",
        "username": admin_username,
        "password": admin_password,
        "scope": "openid profile",
    },
)

token_data = response.json()
admin_token = token_data.get("access_token")

client_response = requests.post(
    "http://localhost:8000/oauth/clients",
    headers={"Authorization": f"Bearer {admin_token}"},
    json={
        "name": "ROPC Login Client",
        "redirect_uris": ["http://localhost:3000/callback"],
        "allowed_grant_types": ["password", "refresh_token"],
        "allowed_scopes": ["openid", "profile", "email", "offline_access"],
        "client_type": "public",  # For testing scripts, using public type is easier
    },
)

client_data = client_response.json()
print(f"Client ID: {client_data['client_id']}")
