# Day22：Debug 面板——Trace 可视化

---

## 一、为什么要做

### 改进前的状态

项目已有可观测性：每次请求生成一个 Trace，记录 Agent 的每一步（LLM 调用、工具调用、token、耗时），存在 `logs/traces.jsonl` + 内存环形缓冲，接口 `GET /debug/traces` 能查到 JSON。

**但数据只以 JSON 形式存在，没有可视化界面。** 两个痛点：

1. **面试没法展示**：面试官问"你的 Agent 怎么工作的？"，我只能掏出 JSON 说"你看这是 trace"。冲击力为零。
2. **开发调试靠猜**：想定位"哪一步慢、哪个工具失败"，得对着原始 JSON 一行行读。

### 为什么做

"可观测性"的价值在于**能看**。数据都有了，缺的只是把它画出来。画出来后：
- 面试时现场播放 Agent 的推理过程——"思考 → 调工具 → 拿结果 → 再思考 → 回答"，面试官亲眼看到，比讲十句都有用
- 调试时一眼看出慢在哪步、哪个工具失败、烧了多少 token

---

## 二、改进方案

### 核心决策：独立页面，不嵌入主前端

| 方案 | 问题 |
|------|------|
| 嵌入主前端 index.html | 主前端是自制的 TRAVERSO 主题，面试要讲，改乱得不偿失 |
| **独立页 static/debug.html** ✅ | 职责单一：主界面=用户聊天，Debug台=看幕后；面试开两个标签对比，冲击力强 |

### 数据流

```
前端 fetch GET /debug/traces?limit=20
  → 渲染左栏请求列表（问题、耗时、token、轮数）
  → 点击某条，取得 steps 数组
  → 重放 = 定时器按当前步数高亮 + 自动滚动
```

**后端零改动**——接口早已存在，今天 100% 前端工作。

### 页面结构（左右分栏）

```
┌ 左栏：请求列表 ┐        ┌ 右栏：Trace 详情/重放 ┐
│ 每行一条：           │        │ ▶播放 ⏸暂停 ⏮⏭步进 速度  │
│  query+耗时+token   │        ├──────────────────────┤
│  "我想去威海三天"    │        │ ● 第1步 · 💭 LLM 思考    │
│  35.1s·13943tok·3轮 │        │ ● 🔧 get_weather       │
│  ...                │        │   威海 → 未找到(标红)  │
│                     │        ├── 统计卡 ────────────┤
│                     │        │ 3轮LLM · 6工具 · 13943tok │
└─────────────────────┘        └──────────────────────┘
```

---

## 三、核心知识点（这次真正学会的）

### 1. 前端 `fetch` + `async/await`

```js
async function loadTraces() {
  const resp = await fetch("/debug/traces?limit=20");
  const data = await resp.json();
  traces = data.traces || [];
}
```

- `fetch()` 向同域名发 GET 请求，`?limit=20` 是 URL 参数
- `await` 等网络返回再继续；函数标 `async` 才能用 `await`
- 网络失败包 `try/catch`，失败给空数组，页面不崩

### 2. `setInterval` 定时器 = "播放"的本质

```js
timer = setInterval(() => {
  if (curStep < stepEls.length - 1) stepTo(curStep + 1);
  else pause();
}, 1200);   // 每 1.2 秒前进一步
```

- `setInterval(函数, 毫秒)` 每隔 N 毫秒执行一次，返回句柄
- `clearInterval(句柄)` 停止
- 速度切换 = 换一个 interval 数值（1x=1200ms / 2x=600ms / 4x=300ms）

### 3. DOM 动态渲染

```js
const div = document.createElement("div");
div.innerHTML = "<div class='head'>🔧 " + s.name + "</div>...";
list.appendChild(div);
```

- `createElement` 造元素 → `innerHTML` 塞内容 → `appendChild` 挂到页面
- `querySelectorAll(".trace-item")` 按 CSS 选择器找一批元素
- `classList.toggle("active", bool)` 加/去高亮类

### 4. CSS 变量 + Grid 布局

```css
:root { --ink:#eaf0ff; --cyan:#7ce8f4; ... }   /* 颜色变量，全页复用 */
.shell { display:grid; grid-template-columns:320px 1fr; }  /* 左320px，右占满 */
```

- 主题用 CSS 变量管理，改一处全变
- `1fr` = 占满剩余宽度，现代布局写法

### 5. 状态区分（失败标红）

```js
if (/未找到|失败|错误|exception/i.test(result)) div.classList.add("bad");
```

- 正则 `.test()` 判断结果文本有没有失败关键词，`i` = 忽略大小写
- 面试官看到失败场景也标红了，说明"我考虑过失败情况"

---

## 四、真实数据展示（面试就放这段）

选一条复杂的 Trace 播放给面试官看：

```
💭 第 1 步 · LLM 思考   deepseek-chat · prompt 3089 → 188 · 2.1s
🔧 get_user_profile     读取用户偏好
🔧 get_weather          威海 → （未找到）0ms
🔧 get_travel_history   读取旅行历史
🔧 search_spots         威海景点 → 无本地库
💭 第 6 步 · LLM 思考   prompt 3622 → 509 · 4.9s
🔧 search_spots         威海美食 → 无本地库
🔧 generate_travel_plan 生成攻略 · 21.1s（最慢）
💭 第 9 步 · LLM 思考   prompt 5991 → 544 · 6.9s
```

**两个观察点**（面试随口说就是加分项）：
1. `generate_travel_plan` 21.1s——因为它内部嵌套了一次 LLM 调用，Trace 记录到工具级
2. `get_weather` 0ms——本地无数据直接返回，没发起网络请求

**真实数据 = 可信度**。面试官看到的是真实运行记录，不是摆拍截图。

---

## 五、遇到的问题

### 问题 1：JS 代码位置不确定

`addEventListener` 那 4 行是立即执行的，不是函数声明，要在 DOM 元素加载完才能跑。因为 `<script>` 标签放在 body 最底部，浏览器读到它时元素已存在，所以放 script 末尾最保险。

**收获**：JS 脚本放 body 底部是标准做法，就是为这个。

### 问题 2：`selectTrace` 未定义

Task 3 点列表会报错，因为 `selectTrace` 是 Task 4 才写的函数。**这是增量开发的正常现象**——每个 Task 只交付一部分，下一 Task 补上。

**收获**：逐步实现时，中间状态有"预期的未完成"很正常，关键是最后验证完整链路。

---

## 六、收获

1. **可观测性 = 数据 + 展示**。只存数据不画出来，价值减半。Debug 面板让"Trace"从工程师的调试工具变成了面试的展示武器
2. **面试讲"Agent"别只讲概念，放真实回放**。"我做了个面板，可以看到 Agent 每一步的思考、每次工具调用和耗时" + 现场播放 → 比任何描述都有说服力
3. **前端原理补了一课**：fetch/async-await（等网络）、setInterval（定时）、createElement（造元素）、CSS 变量 + grid（布局）——这些是任何前端面试都会问的基础
4. **增量开发模式**：分 Task 实现，每 Task 可独立验证（路由通了→布局对→数据来→详情出→播放动），最后拼成完整功能。这也是工程化开发的标准节奏
5. **真实数据最有说服力**：威海这条 trace 有"未找到"、有 21s 的慢工具、有 9 步推理——面试官想看的"Agent 真实行为"全在里面

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
✓ Docker 多阶段构建 + docker-compose 编排
✓ 可观测性 Trace（LLM/token/耗时，JSONL + 环形缓冲）
✓ Debug 面板（Trace 可视化 + 重放 + 统计卡 + 失败标红）
```

## 下一步

- 评估框架（测试场景 + LLM-as-Judge）——体现质量意识
- Multi-Agent 认知（面试高频：你的项目怎么升级成 Planner+Executor）
- http_client.py 接入（半成品收尾）
- Trace 升级 Span 树（记录工具内部的 LLM 调用）
