from __future__ import annotations

from httpx import AsyncClient


async def test_health_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_index_returns_html(client: AsyncClient) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    assert "Nesti" in response.text


async def test_not_found_returns_404(client: AsyncClient) -> None:
    response = await client.get("/nonexistent")
    assert response.status_code == 404
