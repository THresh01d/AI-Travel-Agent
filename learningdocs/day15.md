# Day15：RAG 进阶 + 原生 Function Calling + 项目清理

---

## 一、RAG 中文 Embedding 模型选型

### 学习内容

1. Embedding 模型的语言适配问题
2. BGE 系列中文模型的选择依据
3. ModelScope 国内下载模型
4. ChromaDB 换 embedding 模型的方法

### 改进前的状态

ChromaDB 默认使用 `all-MiniLM-L6-v2`，384 维，英文为主训练的。项目数据全是中文景点描述，用英文模型做语义匹配，效果打折扣。

### 改进方案

调研后选择 `BAAI/bge-small-zh-v1.5`：
- 北京智源研究院出品，专门为中文检索优化
- 在 MTEB 中文榜单名列前茅
- 1024 维，比默认模型的 384 维更精细

## 二、原生 Function Calling

### 学习内容

1. 原生 Function Calling vs Prompt 选工具的本质区别
2. DeepSeek 的 tools 参数使用
3. 工具定义 JSON Schema
4. 结构化参数提取（一次调用同时拿到工具名 + 参数）

### 改进前的状态

`tool_router.py` 用几百字的 Prompt 描述每种工具的触发条件：

messages = [
    {"role": "system", "content": """
    你是一个工具选择器。
    当用户询问推荐城市时返回 {"tool":"recommend"}
    当用户询问历史记录时返回 {"tool":"history"}
    ...
    必须返回JSON格式。不要输出任何解释。
    """},
    {"role": "user", "content": question}
]

问题：

| 问题 | 影响 |
|------|------|
| Prompt 描述不稳定 | AI 偶尔多字少字，JSON 解析炸 |
| 只能拿到工具名 | 参数要再调一次 `extract_travel_info()` |
| 两次 AI 调用 | choose_tool + extract_travel_info，费 token |
| Prompt 越来越长 | 新增工具要改 Prompt，维护负担 |

### 改进后的状态

用 DeepSeek 原生 tools 参数定义工具：

```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "travel",
            "description": "用户想规划一次旅行",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {"type": "string", "description": "目的地城市"},
                    "days": {"type": "integer", "description": "旅行天数"},
                    "budget": {"type": "integer", "description": "旅行预算"},
                    "preference": {"type": "string", "description": "用户偏好"},
                }
            }
        }
    },
    # ... profile, history, recommend, analysis
]

# 调用时传 tools 参数
data = {"model": "deepseek-chat", "messages": messages, "tools": TOOLS}
```

AI 返回的响应里包含 `tool_calls` 字段，工具名和结构化参数一次性拿到：

```json
{
    "tool_calls": [{
        "function": {
            "name": "travel",
            "arguments": "{\"destination\": \"成都\", \"days\": 3, \"budget\": 1500}"
        }
    }]
}
```

### 带来的改变

| | 之前 | 之后 |
|--|------|------|
| 每次对话的 AI 调用次数 | 2 次（choose_tool + extract_travel_info） | 1 次（choose_tool 一次搞定） |
| travel 分支 | `extract_travel_info()` 再提一次 | `args.get("destination")` 直接拿 |
| profile 分支 | `extract_travel_info()` 再提一次 | `args` 直接拿 travel_style、wake_up |
| JSON 稳定性 | Prompt 约束，偶尔抽风 | 模型原生格式，不会多字少字 |
| 工具定义 | 几百字 Prompt | 像写函数文档一样加一个 dict |

### 收获（核心认知）

1. **原生 Function Calling 不是"更快"，是"更省"**：省掉第二次 AI 调用，省 token，省等待时间。速度上 DeepSeek 本身生成时间没变
2. **格式稳定性是最大收益**：Prompt 约束 JSON 总有几率抽风，原生格式是模型专门训练过的，不会多一个"好的"前缀
3. **维护成本降低**：加新工具就是加一个 dict，不用在几百字 Prompt 里找插入位置
4. **本质上是同一件事**：我手写的 Prompt 工具选择器，LangChain 的 Agent，OpenAI 的 Function Calling，都是在做"AI 判断意图 → 调用函数"。理解了本质，用什么框架都一样

---

## 三、项目文件清理

### 删除的文件

| 文件 | 原因 |
|------|------|
| `app/knowledge_base.py` | 旧的 city_spots 字典，已被 RAG 知识库替代 |
| `app/test_rag.py` | Embedding 测试脚本，用完即弃 |
| `main.py` 中 `extract_travel_info` import | Function Calling 替代后不再调用 |

### 保留但不用的

- `ai_service.py` 中的 `extract_travel_info()` 函数——保留备用，哪天想不用 Function Calling 可以回去用

---

## 四、关于 RAG 的深度思考

### 今天最大的认知

> **不是所有 AI 项目都需要 RAG。判断标准：AI 有没有"它不知道但必须知道"的知识。**

旅游常识（景点介绍、城市特色）DeepSeek 比我知道得多。17 条景点数据本质上是在给 AI 喂它已经知道的信息——所以 RAG 在我项目里"粉饰性大于功能性"。

### RAG 真正不可替代的场景

- 公司内部知识库（报销政策、产品文档）→ AI 不可能知道
- 用户产生的私有数据（旅行经验、评价）→ AI 不可能知道
- 实时更新的外部数据（最新价格、天气预报）→ AI 训练数据过时

### 对未来的启发

如果想让 RAG 从"装饰"变成"核心"，需要把知识库从"公开景点介绍"升级为"用户旅行经验"——这是 AI 不可能知道的东西。

---

## 当前项目能力

```
✓ 用户注册/登录（bcrypt 密码哈希）
✓ JWT Bearer Token 认证
✓ 统一对话入口（/agent）
✓ 原生 Function Calling（DeepSeek tools 参数）
✓ RAG 语义搜索（ChromaDB + BGE 中文 Embedding）
✓ AI 旅游攻略生成 + 个性化推荐 + 习惯分析
✓ 用户画像自动提取 + 存储 + 总结
✓ 旅行历史智能存储
✓ async/await 异步 HTTP 层
✓ 中文 Embedding 模型选型（BGE-small-zh-v1.5）
```
