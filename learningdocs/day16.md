# Day16：实时天气 API + SSE 流式输出 + 前端界面 + Function Calling 调优

---

## 一、实时天气 API 接入

### 学习内容

1. 免费天气 API 的选型（Open-Meteo）
2. 城市名 → 经纬度 → 天气数据的两级查询
3. 天气数据注入 LLM Prompt 的方式

### 为什么做

之前的攻略 AI 全靠"猜"天气。用户说"成都三日游"，AI 不知道明天是晴是雨，生成的攻略和实际情况脱节。接入实时天气后，攻略能根据真实天气调整——雨天推荐室内、晴天安排户外。

### 技术选型

选了 **Open-Meteo**，而不是和风天气 / OpenWeatherMap：

| | Open-Meteo | 和风天气 | OpenWeatherMap |
|--|-----------|---------|---------------|
| 免费 | ✅ 完全免费 | ❌ 有调用限制 | ❌ 免费额度低 |
| API Key | ✅ 不需要 | ❌ 需要注册 | ❌ 需要注册 |
| 中文 | ❌ 英文数据 | ✅ 中文 | ✅ 中文 |
| 数据质量 | ✅ 准 | ✅ 准 | ✅ 准 |

不需要 API Key，直接 HTTP GET 就能拿到数据。中文描述自己做了代码→中文的映射字典。

### 实现

新建 `app/services/weather_service.py`：

```python
import httpx

CITY_COORDS = {
    "北京": (39.90, 116.40),
    "成都": (30.57, 104.07),
    # ... 20+ 个城市
}

WEATHER_CODES = {
    0: "晴天", 1: "大部晴", 2: "多云",
    61: "小雨", 63: "中雨", 65: "大雨",
    # ... 20+ 种天气
}

async def get_weather(city: str, days: int = 3) -> str:
    coords = CITY_COORDS.get(city)
    lat, lon = coords

    # 调 Open-Meteo API
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat, "longitude": lon,
        "daily": ["weather_code", "temperature_2m_max", "temperature_2m_min"],
        "forecast_days": min(days, 7),
        "timezone": "Asia/Shanghai",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(url, params=params)
        data = response.json()

    # 拼接成中文描述
    # "成都未来3天天气：
    #  6月14日: 小雨，18°C ~ 25°C
    #  6月15日: 多云，20°C ~ 28°C
    #  6月16日: 晴天，22°C ~ 30°C"
```

### 接入攻略生成

在 `generate_plan()` 的函数签名中加了 `weather: str = ""` 参数，Prompt 中注入天气：

```
天气预报：
{weather if weather else "暂无天气数据"}

请根据天气情况合理调整行程（如雨天建议室内景点，晴天建议户外活动）。
```

### 遇到的问题

**问题：只取了天气数据但没传给 generate_plan**

一开始在 `main.py` 的 travel 分支里 `weather = await get_weather(city, days)` 成功获取了，但传到 `generate_plan()` 时漏了天气参数。

解决：在 `generate_plan()` 函数签名加 `weather: str = ""`，调用时传 `weather=weather`。

### 收获

1. **Open-Meteo 是最佳免费天气 API**：不需要 Key、不限调用次数、数据准。缺点是没有中文，需要自己映射天气代码
2. **外部数据让攻略从"AI 瞎猜"变成"基于事实"**：这是亮点——"用实时数据让 AI 输出更可靠"
3. **函数签名的默认值设计**：`weather: str = ""` 保证向后兼容——不传天气也能正常工作

---

## 二、SSE 流式输出

### 学习内容

1. SSE (Server-Sent Events) 协议原理
2. DeepSeek 的 `stream: true` 参数
3. `httpx.client.stream()` 流式解析
4. `StreamingResponse` + `async def generate()` 的 FastAPI 写法
5. 哪些工具值得流式、哪些不值得

### 为什么做

之前的 `/agent` 调用 DeepSeek 后等 3-10 秒，一次性返回大段文字。这是 API 产品的体验，不是 AI 产品的体验。流式输出（打字机效果）是 AI 产品的标配。

### 实现方案

新增 `/agent/stream` 端点，和原有 `/agent` 并存。DeepSeek 原生支持 `stream: true`，API 返回 SSE 格式：

```
data: {"choices":[{"delta":{"content":"好"}}]}
data: {"choices":[{"delta":{"content":"的"}}]}
...
data: [DONE]
```

### 改动的文件

**新增流式函数：**

| 文件 | 新增函数 | 原因 |
|------|---------|------|
| `ai_service.py` | `generate_plan_stream()` | 攻略生成，几百字，需要流式 |
| `recommend_service.py` | `recommend_city_stream()` | 推荐 3 城市+理由，几百字 |
| `analysis_service.py` | `analyze_user_stream()` | 习惯分析报告，几百字 |

**不改的：** `history`、`profile` 返回一两句话，流式反而鸡肋。

**流式函数的核心写法：**

```python
data = {..., "stream": True}   # 关键参数

async with httpx.AsyncClient(timeout=60) as client:
    async with client.stream("POST", url, headers=headers, json=data) as response:
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                chunk = json.loads(line[6:])        # 去掉 "data: " 前缀
                content = chunk["choices"][0]["delta"]["content"]
                yield content                        # ← yield，不是 return
```

| 非流式 | 流式 |
|--------|------|
| `return` 完整结果 | `yield` 逐字往外送 |
| `client.post(...)` | `client.stream("POST", ...)` |
| `response.json()` | `response.aiter_lines()` |

### 遇到的问题

**问题：Swagger 里流式显示成一堆 Unicode**

`data: {"content": "好的"}` 在 Swagger 里显示为乱码一堆。

原因：Swagger 等响应全部完成才渲染，看不懂 SSE 格式；`\u` 是 JSON 的 Unicode 转义。

不影响实际使用——前端拿到 `好的` 后 `JSON.parse` 会自动解码为 `"好的"`。

### 收获

1. **流式不加速单次请求**：DeepSeek 生成速度没变，只是用户体验从"等 3 秒看一堵墙"变成"看着字一个个往外蹦"
2. **不是所有接口都要流式**：一两句话的回复流式没意义。流式对有几百字输出的工具才有价值
3. **SSE 比 WebSocket 简单得多**：单向推送，不需要双向通信

---

## 三、前端——从 Streamlit 到自定义 HTML

### 学习内容

1. Streamlit 快速原型开发
2. Streamlit 的局限：不能做真正的定制设计
3. 自定义 HTML 前端替代 Streamlit
4. 前端设计——"手绘旅行日志"美学方向

### Streamlit 阶段

写了 `streamlit_app.py`，一个聊天页面，侧边栏登录 + 流式响应。跑通了，但遇到问题：

**问题：对话历史消失**

每次问新问题，之前的回复不见了。

原因：`st.session_state.messages.append()` 这行漏写了。assistant 回复显示在页面上但没存进状态。

解决：加上 append 那行，每次流式结束后存入 session_state。

**Streamlit 的局限：**

设计自由度低——字体、颜色、布局都被 Streamlit 框架限制。做不出真正有审美个性的界面。

### 自定义 HTML 阶段

放弃了 Streamlit，写了一个独立的 HTML 前端页面：

- 文件位置：`static/index.html`
- 访问地址：`http://127.0.0.1:8000/app`
- 纯 HTML + CSS + JS，不依赖任何前端框架
- 通过 `fetch` 调用后端 `/agent/stream`，用 `ReadableStream` 解析 SSE

**设计方向："手绘旅行日志"（Wanderer's Journal）**

- 纸张质感背景（CSS 噪点纹理模拟）
- 左侧皮装订线 + 活页孔
- 消息显示为拍立得卡片，带胶带效果和轻微旋转
- 字体选型：毛笔手写体（Long Cang）+ 草书（Caveat）+ 衬线正文（ZCOOL XiaoWei）
- 米黄/棕色墨水色调，避免纯黑白
- 防印章按钮、虚线分割、日期印章等细节

**设计原则（来自 frontend-design skill）：**

- 不用 Inter/Roboto/Arial 等"AI 默认字体"
- 有明确的美学方向（手工/怀旧/纸张）
- 用细节营造质感：胶带、旋转、阴影、纹理
- 每次交互都有动画反馈（拍立得掉落动画、光标闪烁）

**技术实现：**

```javascript
// SSE 流式解析
const reader = resp.body.getReader();
const dec = new TextDecoder();
let buf = '';

while(true) {
  const {done, value} = await reader.read();
  if(done) break;
  buf += dec.decode(value, {stream:true});
  // 按行解析 "data: {...}" 格式
}
```

**CORS 配置：**

自定义 HTML 运行在浏览器上，请求后端 API 时浏览器会做跨域检查。在 `main.py` 加了 `CORSMiddleware`，允许所有来源访问。

**静态文件路由：**

```python
@app.get("/app")
def serve_frontend():
    return FileResponse("static/index.html")
```

---

## 四、Function Calling 路由修复

### 问题

用户说"我想去成都玩两天"，AI 不断路由到 `profile` 或 `recommend`，就是不选 `travel`。

### 原因

`tool_router.py` 的 system prompt 只有一句话："你是一个旅行助手。根据用户的话选择合适的工具。"AI 没有足够的上下文区分"在聊天"和"在规划旅行"。

### 解决

把 system prompt 改成明确的规则：

```python
"严格按以下规则选择工具：
1. 用户说了具体城市名 + 天数 → 选 travel
2. 用户请求推荐目的地 → 选 recommend
3. 用户表达偏好/习惯 → 选 profile
4. 用户要求分析自己 → 选 analysis
5. 用户问去过哪里 → 选 history

关键：只要用户说了具体城市名，就选 travel。不要选 recommend 或其他工具。"
```

同时把 travel 的 `destination` 参数设为必填，让 AI 明确知道必须提取城市名。

### 收获

1. **Function Calling 不是魔法**：AI 仍然需要清晰的规则才能正确路由
2. **Prompt 仍然重要**：换成 function calling 不代表 Prompt 不重要了，只是格式从 JSON 约束变成了工具描述
3. **required 参数有语义价值**：即使代码层面不强制，也能引导 AI 的行为

---

## 今日项目能力

```
✓ 用户注册/登录（bcrypt 密码哈希）
✓ JWT Bearer Token 认证
✓ 统一对话入口（/agent + /agent/stream）
✓ 原生 Function Calling（DeepSeek tools 参数）
✓ RAG 语义搜索（ChromaDB + BGE 中文 Embedding）
✓ 实时天气 API（Open-Meteo 免费天气）
✓ AI 攻略生成 + 推荐 + 分析
✓ 用户画像自动提取 + 存储 + 总结
✓ 旅行历史智能存储
✓ async/await 异步 HTTP 层
✓ 实时天气 API 接入（Open-Meteo，免费无需 Key）
✓ SSE 流式输出（travel/recommend/analysis）
✓ 自定义 HTML 前端（手绘旅行日志风格）
```

## 下一步

- 多轮对话（带上下文记忆，不只是单轮问答）
- Docker 部署
- 代码拆分（main.py 300+ 行太长了）
