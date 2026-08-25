from __future__ import annotations

from httpx import AsyncClient


async def test_health_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_index_redirects_to_dashboard(client: AsyncClient) -> None:
    response = await client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert "/dashboard" in response.headers["location"]


async def test_not_found_returns_404(client: AsyncClient) -> None:
    response = await client.get("/nonexistent")
    assert response.status_code == 404
