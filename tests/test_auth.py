"""
认证模块集成测试
覆盖 /auth/login 和 /auth/me 端点
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_missing_credentials(client: AsyncClient):
    """缺少用户名密码应返回 422（Pydantic 校验失败）"""
    resp = await client.post("/auth/login", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """错误密码应返回 401"""
    resp = await client.post("/auth/login", json={
        "username": "nonexistent",
        "password": "wrong",
    })
    assert resp.status_code == 401
    assert "用户名或密码错误" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """健康检查端点应返回 200"""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_me_without_auth(client: AsyncClient):
    """未认证访问 /auth/me 应返回 401"""
    resp = await client.get("/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_rate_limit(client: AsyncClient):
    """登录限流：连续 7 次登录请求，第 7 次应被限流"""
    for i in range(6):
        resp = await client.post("/auth/login", json={
            "username": "nonexistent",
            "password": "test",
        })
        assert resp.status_code in (401, 429)
    # 第 7 次应被限流
    resp = await client.post("/auth/login", json={
        "username": "nonexistent",
        "password": "test",
    })
    assert resp.status_code == 429
