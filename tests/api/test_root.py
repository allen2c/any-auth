import pytest
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_api_root_health(
    test_api_client: TestClient,
):
    response = test_api_client.get("/health")
    assert response.status_code == 200, response.text
