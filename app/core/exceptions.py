"""
异常层次结构 — 每种错误有对应的 HTTP 状态码和中文消息
  - 每种异常自带 status_code + 中文 user_message
  - 中间件统一捕获，返回 {"error": "中文消息"} 而不是 traceback
  - 日志里能看到异常类型，快速定位问题
"""


class AppException(Exception):
    """所有自定义异常的基类"""
    status_code: int = 500
    user_message: str = "服务内部错误"

    def __init__(self, user_message: str | None = None, detail: str = ""):
        self.user_message = user_message or self.user_message
        self.detail = detail  # 给开发者看的详细信息，不返回给用户
        super().__init__(self.user_message)


# ---- 认证相关 (401) ----
class AuthError(AppException):
    status_code = 401
    user_message = "认证失败"


class InvalidTokenError(AuthError):
    user_message = "登录已过期，请重新登录"


class InvalidCredentialsError(AuthError):
    user_message = "用户名或密码错误"


# ---- 外部服务相关 (502) ----
class ExternalServiceError(AppException):
    status_code = 502
    user_message = "外部服务暂时不可用，请稍后重试"


class DeepSeekAPIError(ExternalServiceError):
    user_message = "AI 服务暂时不可用，请稍后重试"


class WeatherAPIError(ExternalServiceError):
    user_message = "天气服务暂时不可用"


class DatabaseError(ExternalServiceError):
    user_message = "数据库服务暂时不可用"


# ---- Agent 相关 ----
class AgentError(AppException):
    status_code = 500
    user_message = "AI 处理时遇到问题，请换个方式描述您的需求"


class MaxIterationsExceeded(AgentError):
    user_message = "请求比较复杂，AI 在多次尝试后仍未完成"


class ToolExecutionError(AgentError):
    user_message = "工具执行失败"


# ---- 请求校验 (422) ----
class ValidationError(AppException):
    status_code = 422
    user_message = "请求参数有误"
