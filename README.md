# AI-Travel-Agent · 手写 ReAct 智能旅行规划 Agent

一个基于 **手写 ReAct Agent Loop** 的智能旅行规划助手。用户用自然语言描述目的地、时间和心情，Agent 通过多步推理自主编排工具，整合实时天气、景点知识与个人偏好，生成个性化旅行攻略。

> **核心亮点**：不依赖 LangChain / LangGraph，Agent Loop 全部手写——工具注册表、原生 Function Calling、结果回填、轮次终止、可观测性。

---

## ✨ 功能特性

- **ReAct 多步推理**：Agent 自主决定调哪些工具、调几次、什么顺序（思考 → 调工具 → 观察 → 再思考）
- **9 个细粒度工具**：实时天气 / 景点搜索 / 偏好读写 / 历史记录 / 目的地推荐 / 风格分析 / 行程生成
- **原生 Function Calling**：基于 DeepSeek 官方 tools 参数，工具错误以字符串回填让 Agent 自主纠正
- **SSE 流式输出**：实时推送 Agent 的"思考 → 工具调用 → 结果"全过程
- **可观测性 Trace**：记录每轮 LLM 的 token 与耗时、每次工具的参数与结果，JSONL + 内存环形缓冲
- **Debug 可视化面板**：Trace 回放 / 步进 / 失败标红，直观展示 Agent 推理过程
- **用户体系**：注册 / 登录（bcrypt 密码哈希 + JWT 认证），画像、历史、对话按用户隔离
- **生产化工程**：Pydantic Settings 配置、异常层次、全局中间件、MySQL 连接池、HTTP 单例连接池
- **Docker 部署**：多阶段构建 + app / MySQL 双服务编排

---

## 🛠️ 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.12 · FastAPI · uvicorn |
| Agent | 手写 ReAct Loop · DeepSeek 原生 Function Calling · 工具注册表 |
| 数据 | MySQL（PyMySQL + DBUtils.PooledDB 连接池） |
| 认证 | bcrypt 密码哈希 · JWT Bearer Token（24h 过期） |
| 可观测性 | 自定义 Trace · JSONL 持久化 · SSE 事件流 |
| 前端 | 原生 HTML / CSS / JavaScript（TRAVERSO 暗色主题，无框架） |
| 部署 | Docker 多阶段构建 · docker-compose |

---

## 🏗️ 架构

```
用户输入
   │
   ▼
┌─ Agent Loop（app/core/agent_loop.py）─────────────┐
│  for iteration in 1..MAX_ITERATIONS:             │
│    1. 调 DeepSeek（带 9 个工具定义）               │
│    2. 有 tool_calls？→ 执行工具 → 回填结果 → 再思考 │
│    3. 无 tool_calls → 输出最终回答 → 结束           │
└──────────────┬───────────────────────────────────┘
               │
      ┌────────┴────────────┐
      ▼                     ▼
 工具注册表              Trace 可观测性
 (app/core/            (app/core/trace.py)
  tool_registry.py)     每步 token/耗时/结果
      │
      ├── 实时天气（Open-Meteo）
      ├── 景点检索
      ├── 用户偏好 / 旅行历史（MySQL）
      └── 行程生成（DeepSeek）
```

**一次完整请求的流程**（以"对比成都和大理"为例）：

```
💭 Agent 思考：需要两地的天气、景点、用户偏好
🔧 get_weather(成都) → 天气数据
🔧 get_weather(大理) → 天气数据
🔧 search_spots(成都) → 景点
🔧 search_spots(大理) → 景点
🔧 get_user_profile() → 用户偏好
💭 Agent 再思考：信息足够 → 生成综合对比攻略
```

---

## 🚀 快速开始

### 前置要求

- Python 3.12+
- MySQL 8.0（本地或 Docker）
- DeepSeek API Key

### 1. 配置环境变量

在项目根目录创建 `.env`，填写以下字段：

```bash
# DeepSeek API（必填）
DEEPSEEK_API_KEY=sk-...

# MySQL（本地或 Docker 部署）
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=你的密码
MYSQL_DATABASE=travel_agent

# JWT 密钥（必填，随机字符串）
JWT_SECRET_KEY=your-secret-key
```

> 注意：目前仓库未提供 `.env.example`，请参考 `app/core/config.py` 中的 `Settings` 类字段配置。

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 初始化数据库

先创建数据库（如 `travel_agent`），再启动时由 `app/database.py` 自动建表。

### 4. 启动服务

```bash
uvicorn app.main:app --port 8000
```

打开 http://127.0.0.1:8000 使用前端界面；注册登录后即可开始对话。

### 5. Docker 部署（可选）

```bash
docker-compose up -d
```

会同时启动 FastAPI 应用（:8000）和 MySQL 8.0（:3306）。

---

## 📁 目录结构

```
AI-Travel-Agent/
├── app/
│   ├── main.py                  # FastAPI 入口：路由、SSE、认证
│   ├── database.py              # MySQL 连接池 + 建表
│   ├── core/
│   │   ├── agent_loop.py        # ★ 手写 ReAct Agent Loop
│   │   ├── tool_registry.py     # ★ 工具注册表（schema + handler）
│   │   ├── trace.py             # 可观测性 Trace（JSONL + 环形缓冲）
│   │   ├── http_client.py       # HTTP 单例连接池（复用连接）
│   │   ├── config.py            # Pydantic Settings 统一配置
│   │   ├── exceptions.py        # 异常层次结构
│   │   └── middleware.py        # 全局异常中间件
│   └── services/
│       ├── auth_service.py      # bcrypt + JWT
│       ├── conversation.py      # 对话历史持久化
│       ├── weather_service.py   # Open-Meteo 天气
│       └── dependency.py        # 认证依赖
├── static/
│   ├── index.html               # 主前端（TRAVERSO 暗色主题）
│   └── debug.html               # Debug 面板（Trace 可视化 + 重放）
├── learningdocs/                # 学习记录（day1 ~ day23）
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## 🎯 项目特点

1. **手写 Agent Loop，不依赖 Agent 框架** —— ReAct 循环、tool_calls 解析、结果回填、终止判定、工具注册全部自主实现，Agent 的每一步行为完全可控、可解释
2. **完整执行可观测性** —— Trace 记录每轮推理的 token 与耗时、每次工具调用的参数与结果；Debug 面板支持执行回放与排障
3. **生产化工程能力** —— 配置集中管理、bcrypt + JWT 认证、MySQL / HTTP 连接池、异常层次与全局中间件、Docker 部署
4. **真实数据与持久化** —— 实时天气 API 数据源；用户画像 / 旅行历史 / 对话记录持久化 MySQL，多用户数据隔离

---

## 📄 License

MIT
