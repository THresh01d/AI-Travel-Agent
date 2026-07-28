# Day18：生产硬化 + Python 核心语法学习 + 项目清理

---

## 一、统一配置管理

### 学习内容

1. Pydantic Settings 读取 `.env` 的原理
2. 启动时校验 vs 运行时校验的区别
3. 为什么配置要集中管理

### 改进前的状态

配置散落在项目的各个角落：
- `main.py` 里 `DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")`
- `database.py` 里 `host = os.getenv("MYSQL_HOST")`
- `auth_service.py` 里 `SECRET_KEY = "travel_agent_secret"` ——直接写死在源码里
- `.env` 变量名写错了不会报错，代码跑到那一行才炸，报的是奇怪的 `None` 导致的错误

### 改进方案

新建 `app/core/config.py`，用 Pydantic 的 `BaseSettings` 类集中管理所有配置：

- 没有默认值的变量（如 `deepseek_api_key`、`jwt_secret_key`）→ `.env` 里必须有，否则启动报错
- 有默认值的变量（如 `mysql_host = "localhost"`）→ 不配也能跑
- Pydantic 自动读 `.env`，不需要手动 `load_dotenv()`
- `extra = "ignore"` 让 `.env` 里多余的变量不报错

### 收获

**启动时校验 > 运行时校验。** 之前如果 `.env` 里漏了 `DEEPSEEK_API_KEY`，代码跑到 `os.getenv` 拿到 `None`，然后一路传到 DeepSeek API，`Authorization: Bearer None` → 401 → 用户看到一个莫名其妙的 500。现在启动时就报 `Field required`，一眼知道缺了什么。

---

## 二、JWT 密钥 + Token 过期

### 改进前的状态

`auth_service.py` 第 5 行：`SECRET_KEY = "travel_agent_secret"`。任何人拿到源码都能伪造 JWT Token。且 Token 没有过期时间，一旦签发永久有效。

### 改进方案

- `SECRET_KEY` 移到 `.env` 里：`JWT_SECRET_KEY=你的随机字符串`
- `create_token()` 加了 `exp` 过期时间（默认 24 小时）
- 用 `datetime.now(timezone.utc)` 替代已弃用的 `datetime.utcnow()`

### 遇到的问题

IDE 提示 `utcnow()` 已弃用。原因是 Python 社区推荐使用带时区信息的 datetime，避免夏令时、跨时区等边界问题。改成 `datetime.now(timezone.utc)`。

---

## 三、异常层次结构 + 全局错误中间件

### 学习内容

1. 自定义异常类的继承关系
2. FastAPI 中间件的工作原理
3. 异常捕获的"先具体后泛化"顺序

### 改进前的状态

任何未处理的异常 → FastAPI 自动返回 500 + HTML 格式的 Python traceback。用户看到的是一堆看不懂的报错，日志里也分不清是 API 挂了还是数据库挂了。

### 改进方案

**新建 `app/core/exceptions.py`：**

```
AppException（基类，status_code=500）
├── AuthError（401）
│   ├── InvalidTokenError — "登录已过期"
│   └── InvalidCredentialsError — "用户名或密码错误"
├── ExternalServiceError（502）
│   ├── DeepSeekAPIError — "AI 服务暂不可用"
│   ├── WeatherAPIError — "天气服务暂不可用"
│   └── DatabaseError — "数据库服务暂不可用"
├── AgentError（500）
│   ├── MaxIterationsExceeded
│   └── ToolExecutionError
└── ValidationError（422）
```

每个异常自带 `status_code`（HTTP 状态码）+ `user_message`（返回给用户的中文消息）+ `detail`（给开发者看的调试信息）。

**新建 `app/core/middleware.py`：**

一个 FastAPI 中间件，包裹所有请求：
- `AppException` 子类 → 按设计的 HTTP 状态码和中文消息返回
- 未知异常 → 统一返回 500 + "服务内部错误"，完整 traceback 打日志

### 收获

**中间件 = 安检。** 每个请求进来都要经过它，正常的放行，有问题的拦下来按规则处理。类比机场安检——正常旅客直接通过，带危险品的被拦下按流程处理。

**异常应该分层次。** API 超时、数据库挂了、Token 过期——这是三种完全不同的错误，但之前统一返回 500。现在每种错误有自己的类型、状态码和用户消息。

---

## 四、项目清理

### 删除的文件

| 文件 | 原因 |
|------|------|
| `app/services/ai_service.py` | 被 `tool_registry.py` 的 `_handle_generate_plan` 替代 |
| `app/services/tool_router.py` | 被 `agent_loop.py` + `tool_registry.py` 替代 |
| `app/services/recommend_service.py` | 被 `tool_registry.py` 的 `_handle_recommend` 替代 |
| `app/services/analysis_service.py` | 被 `tool_registry.py` 的 `_handle_analyze` 替代 |
| `app/services/summary_service.py` | 旧的 profile/history 摘要，Agent 不调了 |
| `app/services/agent_service.py` | 旧的数据库读取封装，不调了 |
| `streamlit_app.py` | 已被 `static/index.html` 替代 |

services 目录从 12 个文件降到 5 个（`auth_service.py`、`conversation.py`、`dependency.py`、`weather_service.py`、`__init__.py`）。

---

## 五、Python 核心语法学习

### 学习内容

1. `async def` / `await` — 异步不堵车
2. `yield` — 陆续吐出数据，不一次性返回
3. `async for` — 在异步函数里遍历生成器
4. `try/except` — 防爆炸，不是查问题
5. `from...import` — 文件之间的通信
6. f-string — 字符串里塞变量
7. 类型标注 `: str` / `-> str` / `| None` — 告诉别人参数和返回值类型
8. 装饰器 `@app.post("/xxx")` — 注册路由

### 关键认知

| 概念 | 之前以为 | 现在知道 |
|------|---------|---------|
| `try/except` | 用来查问题在哪 | 用来让问题不要炸整个程序。出错返回一句话给 Agent，让它自己决定下一步 |
| `return` vs `yield` | 都差不多 | `return` 是一次性交卷，`yield` 是陆续给东西。流式输出靠的就是 yield |
| Agent Loop | 以为要多 Agent 分工 | 一个 Agent + while 循环就够了。Multi-Agent 是进阶话题 |

### 收获

1. **`yield` 是流式输出的基础。** 没有 yield 就没有"打字机效果"，用户只能白屏等 5 秒看最终结果
2. **`try/except` 和 Agent 特别契合。** 普通后端 try/except 是返回错误给用户。Agent 的 try/except 是返回错误描述给 LLM——让 LLM 自己决定"这个工具失败了，我换个思路"
3. **语法不是死记硬背的。** 看代码的时候问"为什么这里用 async 而不是普通 def？""为什么这里用 yield 而不是 return？"——答案就是设计意图

---

## 六、项目文件变更

### 新增
- `app/core/config.py` — Pydantic Settings 统一配置
- `app/core/exceptions.py` — 异常层次结构
- `app/core/middleware.py` — 全局错误处理中间件
- `app/core/http_client.py` — 共享 httpx 客户端（备用）

### 修改
- `app/main.py` — `load_dotenv` + `os.getenv` → `settings`，注册中间件
- `app/database.py` — `os.getenv` → `settings`
- `app/services/auth_service.py` — 硬编码 SECRET_KEY → 读配置，JWT 加过期时间
- `.env` — 加 `JWT_SECRET_KEY`

### 删除
- `app/services/` 下 6 个不再使用的文件
- `streamlit_app.py`

---

## 当前项目能力

```
✓ 用户注册/登录（bcrypt 密码哈希）
✓ JWT Bearer Token 认证（24 小时过期）
✓ ReAct Agent Loop（多轮推理 + 多工具编排）
✓ 原生 Function Calling（DeepSeek tools 参数）
✓ 9 个细粒度工具（Agent 自主决定调用顺序）
✓ AI 攻略生成 + 推荐 + 分析
✓ 用户画像自动提取 + 存储 + 总结
✓ 旅行历史智能存储
✓ 实时天气 API（Open-Meteo，免费无需 Key）
✓ SSE 结构化事件流（thinking/tool_call/tool_result/content/done）
✓ async/await 异步全链路
✓ 自定义 HTML 前端（手绘旅行日志风格）
✓ Pydantic Settings 统一配置（启动时校验）
✓ 异常层次结构 + 全局错误中间件
✓ 项目清理：services 从 12 个文件精简到 5 个
```

## 下一步

- MySQL 连接池（database.py 每次新建连接 → DBUtils.PooledDB 复用）
- httpx 共享客户端（tool_registry.py 的 AsyncClient 改用 http_client.py 单例）
- 可观测性（结构化 Trace：每步 LLM 调用/token/耗时）
- 评估框架（测试场景 + LLM-as-Judge）
