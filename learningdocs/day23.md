# Day23：共享 HTTP 客户端——连接池复用

---

## 一、为什么要做

### 改进前的状态

项目里有 **5 处**地方直接 `async with httpx.AsyncClient(timeout=60) as client:`，每次发请求都新建一个客户端：

| 位置 | 干什么 |
|---|---|
| agent_loop.py 主循环 | 每一轮推理都调一次 DeepSeek |
| tool_registry.py × 3 | 生成攻略 / 推荐目的地 / 分析风格 |
| weather_service.py | 查天气 |

**问题 1：每次新建 TCP 连接 + TLS 握手，浪费 50-100ms。** Agent 一轮循环调一次 DeepSeek，可能循环 3-5 轮，每轮都重新握手，全是重复开销。

**问题 2（更隐蔽）：http_client.py 是"假单例"。** 文件注释写着"全局单例，连接池复用"，但实现是：

```python
def get_deepseek_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(...)   # 每次调用都新建一个！
```

它只是把"创建代码"抽成了函数，**没有缓存变量、没有惰性创建，根本不存在复用**。注释说的是目标，代码没做到。

### 为什么做

"复用连接"是后端性能的常识级优化。当时写了文件却没用上，等于一个**半成品**。

---

## 二、核心改动

### 1. http_client.py 从假单例变真单例

三个要素：
- 模块级缓存变量 `_deepseek_client = None`
- `global` 声明
- `if _deepseek_client is None:` 惰性创建，之后永远返回同一个实例

```python
_deepseek_client = None

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
```

### 2. 5 处散落调用全部接入单例

`async with httpx.AsyncClient(...) as client:` → `client = get_deepseek_client()`，去掉 `async with`。

### 3. api_key 参数链清理

原来 api_key 从 `run_agent_loop` 一路传到 9 个 handler。删掉 headers 后 api_key 变成"接了不用"的死参数。整条链清理后，**密钥只经 settings 注入单例构造一次**，其余地方一律不传。

### 4. main.py lifespan 退出时释放连接池

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await get_deepseek_client().aclose()
    await get_weather_client().aclose()
```

---

## 三、核心知识点（这次真正学会的）

### 1. 单例 = 缓存变量 + 惰性创建

```python
_deepseek_client = None          # ① 缓存变量

def get_deepseek_client():
    global _deepseek_client      # ② global：改的是模块顶层那个变量
    if _deepseek_client is None: # ③ 惰性创建：只在第一次
        _deepseek_client = ...   #    创建新实例
    return _deepseek_client      # ④ 之后永远返回同一个
```

**"复用"的本质 = 第二次调用返回第一次建的那个。** 没有缓存变量，"复用"就不存在。

### 2. `async with` 会关闭连接，所以单例模式不能用它

```python
async with httpx.AsyncClient() as client:   # 退出块时自动 client.aclose()
    ...
```

单例模式下如果还用 `async with`，**块结束时单例就被关掉了**，下次调用拿到已关闭的连接直接报错。所以单例模式是：

```python
client = get_deepseek_client()   # 拿到常驻实例，不关闭
await client.post(...)           # 用完不关，下次继续用
```

### 3. 异步的本质是 `await`，不是 `async with`

`async with` 是**资源管理**（进入/退出时做什么），`await client.post()` 才是**异步 I/O**。删掉 `async with`，`await client.post()` 依然异步——事件循环照样能处理其他请求。

### 4. 密钥单一注入点

重构前 api_key 在 main → agent_loop → execute_tool → 9 个 handler 之间传递。重构后：

```
config.py 的 deepseek_api_key
  └─ 只在 http_client.py 构造单例时用一次（拼认证头）
       └─ 所有请求复用这一个已带 key 的连接池
```

密钥只在一个地方出现，**这是安全实践**——面试官问"API key 怎么管理"，这就是标准答案。

### 5. 接口一致性 vs 死代码

9 个 handler 里 6 个**从没用过** api_key，但签名统一写成 `(api_key, args, user_id)`——这叫接口一致性（执行器统一调用方便）。删掉后统一为 `(args, user_id)`。判断标准：**签名是为调用方服务的，参数删了要保证调用方也同步改**。

---

## 四、遇到的问题

### 问题 1：误以为是 headers 没删干净

用户说"删没用的 headers"，我第一反应以为 headers 死代码还在。实际 headers 早就删完了，真正没用的是 **api_key 参数**（headers 删除后它变成孤儿）。这说明**"没用的东西"要区分是变量还是参数**——都要查调用链。

### 问题 2：6 个 handler 的 api_key 从没用过，但也要删

原以为只删 3 个用过 api_key 的 handler（generate_plan/recommend/analyze），实际剩下 6 个**签名里有、函数体里从没用过**的也要删。因为 `execute_tool` 是统一入口，它删了 api_key 参数，**所有被它调用的 handler 签名必须跟着删**，否则运行时报"缺少参数"。

**教训**：改一个签名，所有调用它的人都要跟上。这是 Python 传参的连锁反应。

### 问题 3：删完参数，main.py 的 settings 变成死代码

删除 `settings.deepseek_api_key` 调用后，main.py 里 `from app.core.config import settings` 没人用了。IDE 提示"未存取 settings"，顺手删掉了 import。

**收获**：每次删代码后，**要重新检查 import 有没有变死**。IDE 的 Hint 会提示"未存取"，这是很实用的检查手段。

---

## 五、收获

1. **单例 = 缓存变量 + 惰性创建**。注释写了"单例"不代表实现了单例，看代码要看到"有没有缓存变量"
2. **`async with` 会关闭连接**——这是单例模式不能用它、必须 `client = get_...()` 的直接原因
3. **异步 ≠ async with**。异步是 `await client.post()`，async with 只是资源管理
4. **删参数的连锁反应**：改签名要同步改所有调用方，删完再查 import 死代码
5. **好的重构是"删比加多"**：88 行新增、112 行删除——用更少的代码实现更强的功能（连接复用）

---

## 当前项目能力

```
✓ 用户注册/登录（bcrypt 密码哈希）
✓ JWT Bearer Token 认证（24 小时过期）
✓ ReAct Agent Loop（多轮推理 + 多工具编排）
✓ 原生 Function Calling（DeepSeek tools 参数）
✓ 9 个细粒度工具（Agent 自主决定调用顺序）
✓ 用户画像 + 旅行历史 + 对话历史持久化（全 MySQL）
✓ 实时天气 API（Open-Meteo）
✓ SSE 结构化事件流
✓ Pydantic Settings 统一配置 + 异常层次 + 全局中间件
✓ MySQL 连接池（DBUtils.PooledDB）
✓ 共享 HTTP 客户端（单例连接池复用 + 密钥单一注入 + lifespan 释放）
✓ Docker 多阶段构建 + docker-compose 编排
✓ 可观测性 Trace（LLM/token/耗时，JSONL + 环形缓冲）
✓ Debug 面板（Trace 可视化 + 重放 + 统计卡 + 失败标红）
```

## 下一步

- 私人电台 Demo 模式（脱敏示例歌库 + 启动开关）——面试能现场演示
- 私人电台反馈闭环（点赞/讨厌/听腻 → 可解释重排）
- 私人电台音乐画像（SQL 聚合 → 标签云展示）
- Docker 真正跑一次（Dockerfile 写了但没验证过）
- Trace 升级 Span 树（记录工具内部的 LLM 调用）
