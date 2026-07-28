"""
共享 HTTP 客户端 — 复用连接，避免每次请求重新握手

之前的问题：
  - 每个 service 里 async with httpx.AsyncClient() as client
  - 每次请求新建 TCP 连接 → HTTPS 握手 → 浪费 50-100ms
  - 没有统一的超时和重试配置

现在：
  - 全局单例，连接池复用
  - 统一超时配置
"""

import httpx
from app.core.config import settings


def get_deepseek_client() -> httpx.AsyncClient:
    """DeepSeek API 客户端 — 带认证头的连接池"""
    return httpx.AsyncClient(
        base_url="https://api.deepseek.com",
        timeout=httpx.Timeout(60.0),
        limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        headers={
            "Authorization": f"Bearer {settings.deepseek_api_key}",
            "Content-Type": "application/json",
        },
    )


def get_weather_client() -> httpx.AsyncClient:
    """Open-Meteo 天气 API 客户端 — 无需认证"""
    return httpx.AsyncClient(
        base_url="https://api.open-meteo.com",
        timeout=httpx.Timeout(15.0),
        limits=httpx.Limits(max_keepalive_connections=2),
    )
