# Day21：可观测性——Trace 系统

---

## 一、为什么要做

### 改进前的状态

Agent 是一个黑盒。调试全靠 `print` 和猜：

```python
print("调用了工具", tool_name)      # 散落在代码各处的临时打印
print("LLM返回了", result)
```

问题：

| 问题 | 后果 |
|------|------|
| 不知道 LLM 被调了几次 | 无从判断 Agent 是不是在"绕圈"（反复调同一个工具） |
| 不知道烧了多少 token | 一次对话多少钱、哪里最贵，完全没概念 |
| 不知道每个工具花了多久 | 慢在哪一步、是不是天气接口挂了，全靠猜 |
| 没有落盘记录 | 请求结束后什么证据都没有，没法复盘 Agent 的决策过程 |

**本质：Agent 的核心价值是"多步推理 + 工具编排"，但你看不到它在推理什么、编排了什么。看不见就无法调试、无法改进、无法面试时讲清楚。**

---

## 二、Trace 设计

### 核心思想

**每次用户请求生成一个 Trace（执行轨迹），把 Agent 做的每一步都记下来。**

一个 Trace 记录三类信息：

| 类型 | 记录什么 | 例子 |
|------|---------|------|
| `llm_call` | 每次调用 DeepSeek：模型、输入 token、输出 token、耗时 | `{"model":"deepseek-chat", "prompt_tokens":2571, "duration_ms":2138}` |
| `tool_call` | 每次调用工具：工具名、参数、耗时、结果摘要 | `{"name":"get_weather", "args":{"city":"呼和浩特"}, "result":"（未找到天气数据）"}` |
| `totals` | 汇总：LLM 次数、工具次数、总 token、总耗时 | `{"llm_calls":3, "tool_calls":6, "total_tokens":12080, "duration_ms":30669}` |

### 数据结构（真实示例）

一次"我想去呼和浩特玩三天"的完整 Trace：

```json
{
  "trace_id": "35f31bddb6f4",
  "user_id": 4,
  "query": "我想去呼和浩特玩三天",
  "steps": [
    {"type":"llm_call",  "model":"deepseek-chat", "prompt_tokens":2571, "completion_tokens":186, "duration_ms":2138},
    {"type":"tool_call", "name":"get_weather", "args":{"city":"呼和浩特","days":3}, "duration_ms":0, "result":"（未找到呼和浩特的天气数据）"},
    {"type":"tool_call", "name":"search_spots", "args":{"query":"呼和浩特景点美食","top_k":5}, "duration_ms":0, "result":"未在本地知识库中找到...请直接推荐"},
    {"type":"tool_call", "name":"get_user_profile", "args":{}, "duration_ms":2, "result":"travel_style:自由行..."},
    {"type":"tool_call", "name":"get_travel_history", "args":{}, "duration_ms":1, "result":"天津/北京/平潭岛/威海..."},
    {"type":"llm_call",  "prompt_tokens":3076, "completion_tokens":493, "duration_ms":5005},
    {"type":"tool_call", "name":"generate_travel_plan", "args":{"city":"呼和浩特","days":3,"budget":3000}, "duration_ms":18258, "result":"好的，根据您的要求..."},
    {"type":"tool_call", "name":"save_travel_history", "args":{"city":"呼和浩特","days":3,"budget":3000}, "duration_ms":3, "result":"已保存旅行记录"},
    {"type":"llm_call",  "prompt_tokens":5244, "completion_tokens":510, "duration_ms":5257}
  ],
  "totals": {"llm_calls":3, "tool_calls":6, "total_tokens":12080, "duration_ms":30669}
}
```

**读这条 Trace = 重放一遍 Agent 的全部行为**：先思考 → 查天气失败 → 搜景点无本地库 → 读画像和历史 → 再思考 → 生成攻略（18 秒，最慢）→ 存历史 → 最后整理成回答。

---

## 三、存储策略：双通道

为什么记两处？

| 存储 | 特点 | 用途 |
|------|------|------|
| `logs/traces.jsonl` 文件 | 追加写，不删除 | 长期档案，可回溯任何一次历史请求 |
| 内存环形缓冲（最近 50 条） | 只留最新的，旧的自动挤掉 | Debug 面板实时查询，不占内存 |

### 环形缓冲是什么

```python
from collections import deque
_ring_buffer = deque(maxlen=50)   # 最多 50 条，满了最旧的自动弹出
```

这解决了一个真问题：**如果 Trace 无限存内存，服务跑一天就 OOM 了。** 环形缓冲保证内存只占 50 条的量级。

### JSONL 是什么

一个文本文件，**每一行是一条独立 JSON**：

```jsonl
{"trace_id":"a1b2...", ...}
{"trace_id":"c3d4...", ...}
```

好处：追加写不破坏旧数据、可以 `tail` 看最新、可以用 `grep` 按关键字搜。是日志文件的业界标准格式。

---

## 四、代码实现

### 1. `app/core/trace.py` — Trace 类

```python
class Trace:
    def __init__(self, user_id, query):
        self.trace_id = uuid.uuid4().hex[:12]   # 12位随机ID
        self.steps = []                          # 每一步
        self.totals = {"llm_calls":0, "tool_calls":0, "total_tokens":0, "duration_ms":0}

    def add_llm_call(self, model, prompt_tokens, completion_tokens, duration_ms):
        # 记一轮 LLM 调用
        self.steps.append({"type":"llm_call", "model":model, ...})
        self.totals["llm_calls"] += 1
        self.totals["total_tokens"] += prompt_tokens + completion_tokens

    def add_tool_call(self, name, args, duration_ms, result_summary):
        # 记一次工具调用（结果只存前200字符，防上下文爆炸）
        self.steps.append({"type":"tool_call", "name":name, "args":args, ...})

    def finish(self):
        # 结束时：写文件 + 进环形缓冲
        _append_to_file(record)
        _ring_buffer.append(record)
```

### 2. `app/core/agent_loop.py` — 三个接入点

```python
# ① 循环开始前：创建 Trace
trace = Trace(user_id, user_message)

# ② 每次调完 DeepSeek：记 LLM 调用（在调用处量耗时）
trace.add_llm_call("deepseek-chat", prompt_tokens, completion_tokens, llm_ms)

# ③ 每次工具执行完：记工具调用（也在调用处量耗时）
trace.add_tool_call(tool_name, args, tool_ms, tool_result)

# ④ 所有 return 路径前：结束 Trace
trace.finish()
```

**关键设计：`trace.finish()` 必须放在每一条 return 路径前**（LLM 挂了、正常回答、异常退出、超 5 轮）。否则某条路径漏调，这条 Trace 就永远不落盘。

### 3. `app/main.py` — 查看入口

```python
@app.get("/debug/traces")
def debug_traces(limit: int = 20):
    """返回最近 N 条 Trace，供调试面板查询"""
    traces = get_recent_traces(limit)
    return {"count": len(traces), "traces": traces}
```

访问 `http://127.0.0.1:8000/debug/traces` 即可实时查看。

---

## 五、遇到的问题

### 问题 1：日志写入失败不能拖垮主流程

如果 `logs/` 目录写不进去（磁盘满、权限问题），Trace 失败不能导致用户请求失败。

解决：`_append_to_file` 整体包在 `try/except` 里，写失败只 `print` 一句警告：

```python
def _append_to_file(record):
    try:
        ...写文件...
    except Exception as e:
        print(f"[trace] 写入失败: {e}")   # 主流程继续
```

### 问题 2：已知盲区——工具内部的 LLM 调用记不到

`generate_travel_plan` 工具内部又调了一次 DeepSeek 生成攻略，所以它耗时 18 秒。但 Trace 只记录到"工具"这一层，**看不到工具内部那次 LLM 请求**。

这不是 bug，是当前 Trace 的粒度是"工具级"。**面试可讲的改进方向**："下一步把 Trace 升级成 Span 树（树形调用链），让工具内部的 LLM 调用也串起来。"

---

## 六、收获

1. **可观测性让 Agent 调试从"猜"变"看"**。以前"为什么 Agent 一直重试某个工具"靠猜，现在翻 Trace 一眼看到它重试了几次、每次结果是什么、花了多久
2. **Trace 和 SSE 是两回事**。SSE 是实时把事件推给前端（正在发生的事），Trace 是事后落盘记录（发生过的事）。前者给人看，后者给机器分析和回放
3. **环形缓冲是控制内存的常用手段**。`deque(maxlen=N)` 一句代码解决"无限累积"的问题，这在日志、指标采集里是标配
4. **JSONL 比 JSON 更适合日志**。一行一条，可追加、可 tail、可 grep，不需要一次性加载整个文件
5. **Token 是 Agent 成本的单位**。一次真实任务 12080 token、30 秒，成本不到一毛钱——面试时能说出"我的 Agent 一次任务 X 秒、Y token、Z 分钱"，是硬实力的体现

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
✓ SSE 结构化事件流（thinking/tool_call/tool_result/content/done）
✓ Pydantic Settings 统一配置（启动时校验）
✓ 异常层次结构 + 全局错误中间件
✓ MySQL 连接池（DBUtils.PooledDB）
✓ Docker 多阶段构建 + docker-compose 编排
✓ 可观测性 Trace（LLM/token/耗时，JSONL + 环形缓冲，/debug/traces 查看）
```

## 下一步

- Debug 面板前端（Trace 数据已有，前端可视化还没做）
- httpx 共享客户端接入（http_client.py 写了但没接进 agent_loop）
- 评估框架（测试场景 + LLM-as-Judge）
- Trace 升级 Span 树（记录工具内部的 LLM 调用）
