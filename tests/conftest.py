from __future__ import annotations

from httpx import ASGITransport, AsyncClient
from pytest import fixture

from app.main import app


@fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
