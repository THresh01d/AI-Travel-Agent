# Day17：路由器 → Agent — ReAct 循环重构 + RAG 移除

---

## 一、什么是 Agent——从路由器到推理循环

### 学习内容

1. 路由器 vs Agent 的本质区别
2. ReAct 模式（Reasoning + Acting）
3. Agent Loop 的手写实现
4. 结构化 SSE 事件流

### 改进前的状态

/agent 端点的架构本质是分类器 + 分发器：

用户输入 → choose_tool() → 选一个工具 → main.py 的 if/elif 执行固定流程 → 返回

每次对话 LLM 只调用一次，选完工具就没它的事了。main.py 的 if/elif 分支 130 行，每个分支是一个写死的工作流。

**致命问题：**

用户说"成都和重庆哪个更适合我？"：

choose_tool → DeepSeek："他没说城市+天数…选 recommend 吧"
→ recommend 分支：一键调 LLM 推荐城市 → 返回
→ 不会查天气、不会读偏好、不会对比

用户说"想去看海，预算两千"：

choose_tool → 可能选 travel（destination=null）
→ travel 分支：city = null or rag_city → 生成空攻略或者炸

### 改进方案

`Agent = while 循环 + 工具结果回传`。

**新建 `app/core/agent_loop.py`：**

```python
messages = [system_prompt, ...history, user_message]

for iteration in range(1, 6):          # 最多 5 轮
    response = await deepseek.chat(messages, tools=TOOLS)

    if response 有 tool_calls:
        执行每个工具
        把工具结果追加到 messages
        continue                         # 回到循环，LLM 重新评估

    if response 有文本:
        return 文本                      # LLM 觉得够了，结束
```

**关键设计决策：**

| 决策 | 原因 |
|------|------|
| max_iterations = 5 | 防无限循环烧 token，复杂查询 2-3 轮够了 |
| 工具结果截断 200 字符（展示用） | 避免上下文爆炸，完整结果存在 trace 里 |
| 每个工具 handler 内部 try/except | 出错返回描述字符串不抛异常，Agent 自己决定下一步 |
| System Prompt 教流程不教规则 | 不写"说城市名就选 travel"，而是写"先收集信息再下结论" |

### 收获

1. **Agent Loop 不是框架才能做的事**：15 行的 while 循环就是 Agent。LangChain 的 AgentExecutor 底层也是这个东西——理解了本质，用什么框架都一样
2. **SSE 从纯文本升级为结构化事件**：thinking / tool_call / tool_result / content / done 五种事件，前端能展示 Agent 的每一步推理
3. **决策从代码移到 LLM**：以前加功能 = 加 elif，现在加功能 = 加工具定义，LLM 自己编排顺序

---

## 二、工具粒度重构

### 学习内容

1. 工具粒度对 Agent 能力的影响
2. 从粗粒度工作流拆为细粒度原子工具

### 改进前的状态

原来 5 个粗工具：travel、profile、history、recommend、analysis。

travel 工具内部做了 6 件事：提取参数 → 存偏好 → RAG 搜索 → 查天气 → 存历史 → 生成攻略。选 travel 就一条路走到底，Agent 没法只查天气或只读偏好。

### 改进方案

**新建 `app/core/tool_registry.py`**，拆成 9 个细粒度工具：

| 工具 | 只做一件事 |
|------|-----------|
| `get_weather(city, days)` | 查城市天气 |
| `search_spots(query)` | 搜本地知识库 |
| `get_user_profile()` | 读用户偏好 |
| `save_user_preference(key, value)` | 存一条偏好 |
| `get_travel_history()` | 读旅行历史 |
| `save_travel_history(city, days, budget)` | 存旅行记录 |
| `generate_travel_plan(city, days, budget, ...)` | 最终生成攻略 |
| `recommend_destinations()` | 推荐目的地 |
| `analyze_travel_style()` | 分析习惯 |

Agent 现在能做的事："对比成都和重庆" → 并行调 `get_weather(成都)` + `get_weather(重庆)` + `search_spots(成都)` + `search_spots(重庆)` + `get_user_profile()` → 综合对比 → 返回。这是原来做不到的。

### 收获

1. **工具粒度决定 Agent 的灵活度**：粗工具绑定死流程，细工具让 LLM 自己编排
2. **工具数量多不影响性能**：每轮并行执行的工具共享一次 LLM 调用，9 个工具和 5 个工具的 token 开销几乎一样

---

## 三、main.py 瘦身

### 改进前的状态

`/agent` 和 `/agent/stream` 两个端点共 200+ 行，核心是一个巨大的 if/elif 树，每个分支内部又有 10-30 行不等的写死流程。

### 改进后的状态

```python
# /agent —— 原来 130 行
async for event in run_agent_loop(api_key, message, user_id, history):
    if event["type"] == "content":
        final_answer = event["text"]
```

```python
# /agent/stream —— 原来 80 行  
async for event in run_agent_loop(...):
    yield f"data: {json.dumps(event)}\n\n"
```

main.py 从 423 行降到 232 行。决策逻辑从 if/elif 移到了 LLM 的循环推理里。

---

## 四、SSE 事件升级

### 学习内容

1. 结构化 SSE 事件的设计
2. 前端如何渲染 Agent 的思考过程

### 改进前的状态

```
data: {"content": "成都是个好地方..."}
data: [DONE]
```

前端只知道来了一坨文字，不知道 Agent 在想什么、调了什么工具。

### 改进方案

新增 5 种事件类型：

```
data: {"type": "thinking", "iteration": 1}
data: {"type": "tool_call", "name": "get_weather", "args": {"city": "成都"}}
data: {"type": "tool_result", "name": "get_weather", "summary": "成都：29-41°C"}
data: {"type": "thinking", "iteration": 2}
data: {"type": "content", "text": "根据天气和偏好，推荐..."}
data: {"type": "done", "stats": {"iterations": 2, "tool_calls": 5, "total_tokens": 1330}}
```

前端改造：
- `content` 事件 → 打字机效果（原来的 behavior）
- `tool_call` 事件 → 显示 `🔍 get_weather…`
- `tool_result` 事件 → 显示 `✓ get_weather 完成`
- `thinking` 和 `done` → 不在内容区显示

### 遇到的问题

**问题：前端不显示任何内容**

原因：原来前端解析 `chunk.content`，新格式是 `chunk.text`。

解决：加类型判断 `if (chunk.type === 'content') full += chunk.text`。

---

## 五、RAG 移除

### 学习内容

1. RAG 的适用场景判断
2. "粉饰性 RAG" 的识别

### 为什么删

- 17 条硬编码内陆城市数据，DeepSeek 训练数据里全有——RAG 没有提供 LLM 不知道的信息
- 用户问"看海"就废——RAG 里只有北京成都重庆武汉等内陆城市
- 启动依赖 torch + sentence_transformers，模型路径硬编码 `./local_model/BAAI/bge-small-zh-v1___5`
- ChromaDB 数据在 `./chroma_data`，换环境不起效

**本质问题：给 LLM 外挂了一个它不需要的知识库。**

### 删除内容

| 删除 | 原因 |
|------|------|
| `app/knowledge/` 整个目录 | 17 条数据 + ChromaDB 初始化 + BGE 模型加载 |
| `main.py` 的 `init_knowledge_base()` 启动调用 | 不再初始化知识库 |
| `tool_registry.py` 的 `search_spots` handler | 改为返回提示"请用你的训练知识推荐" |
| `requirements.txt` 里的 chromadb（建议） | 暂时不需要向量数据库 |

### 收获（核心认知）

1. **RAG 的价值 = 提供 LLM 不知道的信息。** 公开景点介绍、城市特色、常识——LLM 本来就烂熟于心，RAG 纯粉饰
2. **RAG 真正不可替代的场景：**

| 场景 | 例子 |
|------|------|
| 私有数据 | 公司文档、用户个人游记 |
| 实时数据 | 机票价格、酒店空房 |
| 长尾知识 | 小众景点、当地人 tips |

3. **如果以后想加回 RAG**：方向是用户游记（POST /reports → 嵌入 → 搜索用户产生的私有数据）——这才是 LLM 不可能知道的信息

---

## 六、实战效果对比

### 场景1："成都和大理哪个更适合我？"

| | 旧版（路由器） | 新版（Agent Loop） |
|---|---|---|
| LLM 调用次数 | 1 次 | 2 轮 |
| 工具调用 | 1 个（recommend） | 5 个（weather×2 + profile + history + recommend） |
| 利用天气？ | ❌ | ✅ 成都 41°C vs 大理 25°C |
| 利用偏好？ | ❌ | ✅ 匹配"喜欢凉快、静谧" |
| 利用历史？ | ❌ | ✅ 发现去过成都，推荐新目的地 |

### 场景2："想去看海，预算两千，玩两天"

| | 旧版 | 新版 |
|---|---|---|
| 路由 | 可能选 travel（没城市名，destination=null）| Agent 判断：没城市 → 先推荐沿海城市 |
| 结果 | 生成空攻略或错误 | 推荐威海 → 查天气 → 读偏好 → 生成完整攻略 |

---

## 七、项目文件变更

### 新增
- `app/core/__init__.py`
- `app/core/agent_loop.py` — ReAct 执行器（~200 行）
- `app/core/tool_registry.py` — 9 个工具定义 + 执行器（~370 行）

### 修改
- `app/main.py` — 423 行 → 232 行（if/elif 分支 → Agent Loop 调用）
- `static/index.html` — SSE 解析适配新事件格式

### 删除
- `app/knowledge/` 整个目录（`__init__.py`、`spots_data.py`、`vector_store.py`）

---

## 当前项目能力

```
✓ 用户注册/登录（bcrypt 密码哈希）
✓ JWT Bearer Token 认证
✓ ReAct Agent Loop（多轮推理 + 多工具编排）
✓ 原生 Function Calling（DeepSeek tools 参数）
✓ 9 个细粒度工具（Agent 自主决定调用顺序和组合）
✓ AI 攻略生成 + 推荐 + 分析
✓ 用户画像自动提取 + 存储 + 总结
✓ 旅行历史智能存储
✓ 实时天气 API（Open-Meteo，免费无需 Key）
✓ SSE 结构化事件流（thinking/tool_call/tool_result/content/done）
✓ async/await 异步全链路
✓ 自定义 HTML 前端（手绘旅行日志风格）

## 下一步

- 错误处理中间件（异常层次结构、用户友好的错误响应）
- 连接池（MySQL + HTTP 客户端复用）
- 配置管理（Pydantic Settings，消除硬编码 SECRET_KEY）
- 可观测性（结构化 Trace：每步 LLM 调用/token/耗时）
- 用户游记 RAG（真正有价值的知识库方向）
- 评估框架（测试场景 + LLM-as-Judge）
