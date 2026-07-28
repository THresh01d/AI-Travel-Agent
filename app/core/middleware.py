"""
全局异常处理中间件

之前的问题：
  - 任何未捕获的异常 → FastAPI 返回 500 + HTML traceback
  - AppException 定义的异常也没人捕获

现在：
  - AppException → 返回 status_code + 中文 user_message
  - 未知异常 → 返回 500 + "服务内部错误"，traceback 打日志
"""

import traceback
import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from app.core.exceptions import AppException

logger = logging.getLogger("travel_agent")


async def exception_handler_middleware(request: Request, call_next):
    """FastAPI 中间件：包裹所有请求，统一捕获异常"""
    try:
        return await call_next(request)
    except AppException as e:
        # 我们定义的异常 → 按设计的状态码和消息返回
        logger.warning(
            f"[{e.__class__.__name__}] {e.user_message}"
            f"{' | detail: ' + e.detail if e.detail else ''}"
        )
        return JSONResponse(
            status_code=e.status_code,
            content={"error": e.user_message}
        )
    except Exception:
        # 未知异常 → 500，打完整 traceback
        logger.exception("未处理的异常")
        return JSONResponse(
            status_code=500,
            content={"error": "服务内部错误，请稍后重试"}
        )
