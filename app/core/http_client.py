"""
共享 HTTP 客户端 — 复用连接，避免每次请求重新握手

  - 全局单例，连接池复用
  - 统一超时配置
"""

import httpx
from app.core.config import settings

_deepseek_client = None
_weather_client = None

def get_deepseek_client() -> httpx.AsyncClient:
    global _deepseek_client
    if _deepseek_client is None:
        _deepseek_client = httpx.AsyncClient(
            base_url="https://api.deepseek.com",
            timeout=httpx.Timeout(60.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            headers={
                "Authorization": f"Bearer {settings.deepseek_api_key}",
                "Content-Type": "application/json",
            },
        )
    return _deepseek_client


def get_weather_client() -> httpx.AsyncClient:
    global _weather_client
    if _weather_client is None:
        _weather_client = httpx.AsyncClient(
            base_url="https://api.open-meteo.com",
            timeout=httpx.Timeout(15.0),
            limits=httpx.Limits(max_keepalive_connections=2),
        )
    return _weather_client
