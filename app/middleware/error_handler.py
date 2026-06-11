"""
全局异常处理中间件 + 请求ID追踪
确保任何未捕获异常都返回统一的 JSON 错误响应并记录日志
"""
import uuid
import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("student_management")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """为每个请求注入唯一 request_id，便于日志追踪"""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    兜底异常处理器：捕获所有未被路由层捕获的异常
    返回统一结构: {"detail": str, "request_id": str}
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        "Unhandled exception | request_id=%s | path=%s | method=%s",
        request_id, request.url.path, request.method,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "服务器内部错误",
            "request_id": request_id,
        },
    )
