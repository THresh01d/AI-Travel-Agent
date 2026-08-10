# Debug 面板 Implementation Plan

> **执行说明（教学式）:** 本计划按"你动手、我讲解"执行。每步先讲原理，再给要写的代码，你敲完后运行验证。不要一次性读完所有代码——按 Task 顺序，一个 Task 完成再进下一个。每步验证通过后 commit。

**Goal:** 用纯 HTML/CSS/JS 做一个 Trace 可视化 Debug 面板，把 Agent 的思考/工具调用/统计展示出来，支持重放。

**Architecture:** 独立静态页 `static/debug.html`，通过 `fetch` 调已存在的 `GET /debug/traces` 接口拿数据，前端渲染列表 + 详情 + 重放。后端只在 `main.py` 加一个路由。

**Tech Stack:** HTML + CSS + 原生 JS（无框架）、FastAPI FileResponse、SSE 无关（本页只用 fetch）。

## Global Constraints

- **不改动主前端 `static/index.html`**（TRAVERSO 主题是用户作品）
- **不改后端逻辑**：agent_loop.py、trace.py 完全不动
- **样式沿用 TRAVERSO 暗色主题变量**（从 index.html 的 `:root` 复制：--ink/--muted/--line/--panel/--cyan/--violet/--lime/--danger）
- 纯原生 JS，不引入 CDN 框架
- 接口格式固定：`GET /debug/traces?limit=20` → `{count, traces: [{trace_id, user_id, query, steps, totals}]}`
- steps 元素两种：`{"type":"llm_call","model","prompt_tokens","completion_tokens","duration_ms"}` 或 `{"type":"tool_call","name","args","duration_ms","result"}`
- totals 字段：`{"llm_calls","tool_calls","total_tokens","duration_ms"}`

---

### Task 1: 后端路由 + 最简占位页面

**Files:**
- Modify: `app/main.py`（在 serve_frontend 附近加路由）
- Create: `static/debug.html`（最简占位）

**Interfaces:**
- Consumes: 无
- Produces: 路由 `GET /debug` 返回 `static/debug.html`；用户浏览器能打开 `/debug`

- [ ] **Step 1: 后端加路由**

在 `app/main.py` 的 `@app.get("/app")` 下面加：

```python
@app.get("/debug")
def serve_debug_panel():
    return FileResponse("static/debug.html")
```

（`FileResponse` 已经在文件顶部的 import 里了，不用加。）

- [ ] **Step 2: 创建最简占位页 `static/debug.html`**

新建文件 `static/debug.html`，内容：

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <title>TRAVERSO · Agent Trace 调试台</title>
</head>
<body>
  <h1>Debug 面板（占位）</h1>
</body>
</html>
```

- [ ] **Step 3: 验证路由通了**

重启服务：`uvicorn app.main:app --reload`
浏览器打开 `http://127.0.0.1:8000/debug` → 应该看到 "Debug 面板（占位）"

- [ ] **Step 4: Commit**

```bash
git add app/main.py static/debug.html
git commit -m "day22: /debug 路由 + 占位页"
```

**🧑‍🏫 教学点：** 路由 = 一个"地址 → 响应"的对应关系。`@app.get("/debug")` 意思是"访问 /debug 这个地址时，执行下面这个函数"。`FileResponse` 就是把一个文件作为响应发回去。

---

### Task 2: 页面骨架 + TRAVERSO 暗色样式

**Files:**
- Modify: `static/debug.html`（替换占位，写入完整骨架 + 样式）

**Interfaces:**
- Consumes: 无
- Produces: 固定 DOM id：`#list`（左栏列表）、`#detail`（右栏详情）、`#playBtn` `#pauseBtn` `#prevBtn` `#nextBtn`（播放控制）、`#speed`（速度）、`#stats`（统计卡）、`#empty`（空状态）、`#totalCount`（顶部统计）

- [ ] **Step 1: 写页面骨架（HTML 结构）**

把 `static/debug.html` 替换成下面的结构（CSS 下一步写，先保证结构在）：

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>TRAVERSO · Agent Trace 调试台</title>
  <style>
    /* 下一步（Step 2）填这里 */
  </style>
</head>
<body>
  <div class="shell">
    <!-- 左栏 -->
    <aside class="sidebar">
      <div class="brand">TRAVERSO · TRACE</div>
      <div id="totalCount" class="total">暂无记录</div>
      <div id="list" class="list"></div>
    </aside>
    <!-- 右栏 -->
    <main class="main">
      <div class="controls">
        <button id="playBtn">▶ 播放</button>
        <button id="pauseBtn">⏸ 暂停</button>
        <button id="prevBtn">⏮ 上一步</button>
        <button id="nextBtn">⏭ 下一步</button>
        <select id="speed">
          <option value="1200">1x</option>
          <option value="600">2x</option>
          <option value="300">4x</option>
        </select>
      </div>
      <div id="stats" class="stats"></div>
      <div id="detail" class="detail"></div>
      <div id="empty" class="empty">还没有 Trace 记录，先去 /app 用 Agent 聊一句</div>
    </main>
  </div>
  <script>
    // 下一步（Step 3 起）填这里
  </script>
</body>
</html>
```

- [ ] **Step 2: 填 CSS（TRAVERSO 暗色风格）**

把下面 CSS 填进 `<style>` 里（变量直接沿用你主前端的配色）：

```css
:root { --ink:#eaf0ff; --muted:#8e9ab6; --line:rgba(190,207,247,.13); --panel:rgba(15,24,47,.66); --cyan:#7ce8f4; --violet:#9d8cff; --lime:#c7fa76; --danger:#ff8d9d; }
* { box-sizing:border-box; }
body { margin:0; color:var(--ink); background:#080e1d; font-family:'Segoe UI',system-ui,sans-serif; min-height:100vh; }
.shell { display:grid; grid-template-columns:320px 1fr; min-height:100vh; }
.sidebar { border-right:1px solid var(--line); padding:20px 16px; background:rgba(7,13,29,.66); overflow-y:auto; }
.brand { font-weight:800; letter-spacing:.12em; padding-bottom:14px; border-bottom:1px solid var(--line); }
.total { font-size:12px; color:var(--muted); padding:10px 0; }
.list { display:flex; flex-direction:column; gap:8px; }
.trace-item { border:1px solid var(--line); border-radius:12px; padding:10px 12px; cursor:pointer; background:var(--panel); transition:.15s; }
.trace-item:hover { border-color:var(--cyan); }
.trace-item.active { border-color:var(--violet); }
.trace-item .q { font-size:13px; font-weight:600; margin-bottom:4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.trace-item .meta { font-size:11px; color:var(--muted); }
.main { display:flex; flex-direction:column; padding:20px 28px; gap:14px; }
.controls { display:flex; gap:8px; align-items:center; }
.controls button { border:1px solid var(--line); background:rgba(255,255,255,.04); color:var(--ink); border-radius:10px; padding:8px 14px; cursor:pointer; font-size:13px; }
.controls button:hover { border-color:var(--cyan); }
.controls select { border:1px solid var(--line); background:#111b35; color:var(--ink); border-radius:10px; padding:8px; }
.stats { display:flex; gap:18px; font-size:12px; color:var(--muted); border-bottom:1px solid var(--line); padding-bottom:12px; }
.stats b { color:var(--cyan); font-size:14px; margin-right:4px; }
.detail { flex:1; overflow-y:auto; display:flex; flex-direction:column; gap:10px; }
.step { border:1px solid var(--line); border-radius:12px; padding:12px 14px; background:var(--panel); }
.step.llm { border-left:3px solid var(--violet); }
.step.tool { border-left:3px solid var(--cyan); }
.step.bad { border-left:3px solid var(--danger); }
.step.now { outline:2px solid var(--lime); }
.step .head { font-weight:700; font-size:13px; margin-bottom:6px; }
.step .body { font-size:12px; color:var(--muted); line-height:1.6; word-break:break-all; }
.step .dur { font-size:11px; color:var(--cyan); }
.empty { color:var(--muted); font-size:14px; text-align:center; padding-top:80px; }
```

- [ ] **Step 3: 验证布局**

刷新 `/debug` → 看到左右分栏、顶部控制按钮、空状态提示。按钮点了没反应是正常的（JS 还没写）。

- [ ] **Step 4: Commit**

```bash
git add static/debug.html
git commit -m "day22: Debug 面板骨架 + TRAVERSO 样式"
```

**🧑‍🏫 教学点：**
- CSS 变量 `:root{--ink:...}`：定义"颜色变量"，全页面复用，改一处全变。面试可以说"主题用 CSS 变量管理"
- `display:grid; grid-template-columns:320px 1fr`：左右分栏的现代写法，`1fr` = "占满剩余宽度"
- `id` 是 JS 找元素的"门牌号"——后面所有 JS 都用 `document.getElementById(...)` 找这些 id

---

### Task 3: 加载数据 + 渲染请求列表

**Files:**
- Modify: `static/debug.html`（在 `<script>` 里写 JS）

**Interfaces:**
- Consumes: `GET /debug/traces?limit=20`（返回格式见 Global Constraints）
- Produces: 函数 `loadTraces()` → 渲染 `#list`；全局变量 `traces` 保存当前列表；函数 `fmtTime(ms)`（毫秒→人类可读）

- [ ] **Step 1: 写 fetch + 渲染列表的 JS**

把 `<script>` 里填上：

```js
let traces = [];          // 当前拿到的全部 trace
let current = null;       // 当前选中的 trace

// 毫秒 → "12.3s" 或 "45ms"
function fmtTime(ms) {
  if (ms >= 1000) return (ms / 1000).toFixed(1) + "s";
  return ms + "ms";
}

// 请求 /debug/traces 并渲染左栏列表
async function loadTraces() {
  try {
    const resp = await fetch("/debug/traces?limit=20");
    const data = await resp.json();
    traces = data.traces || [];
  } catch (e) {
    traces = [];
  }
  renderList();
}

function renderList() {
  const list = document.getElementById("list");
  const count = document.getElementById("totalCount");
  list.innerHTML = "";
  count.textContent = "共 " + traces.length + " 条记录";
  if (traces.length === 0) return;
  traces.forEach((t, i) => {
    const item = document.createElement("div");
    item.className = "trace-item" + (i === 0 ? " active" : "");
    item.innerHTML =
      '<div class="q">' + (t.query || "(无问题)") + "</div>" +
      '<div class="meta">' + fmtTime(t.totals.duration_ms) +
      " · " + t.totals.total_tokens + " tok · " +
      t.totals.llm_calls + "轮LLM</div>";
    item.addEventListener("click", () => selectTrace(i));
    list.appendChild(item);
  });
}

loadTraces();   // 页面加载完就请求一次
```

（`selectTrace` 在 Task 4 定义，先不管，点列表暂时会报错——正常。）

- [ ] **Step 2: 验证列表渲染**

先用 Agent 聊一句（`/app` 里），再刷新 `/debug` → 左栏应该出现几条记录，显示问题、耗时、token、轮数。**如果没数据**，先确认 `/debug/traces` 接口直接访问有内容。

- [ ] **Step 3: Commit**

```bash
git add static/debug.html
git commit -m "day22: Debug 面板加载并渲染请求列表"
```

**🧑‍🏫 教学点：**
- `async/await`：`await fetch(...)` 意思是"等网络返回再继续"。函数标 `async` 才能用 `await`
- `fetch("/debug/traces?limit=20")`：向同域名发 GET 请求。`?limit=20` 是 URL 参数
- `createElement` + `innerHTML`：动态造 HTML 元素塞进页面。`forEach` 是"对数组每个元素做一遍"
- `addEventListener("click", ...)`：给元素绑"点击事件"，点了就执行函数

---

### Task 4: 点击查看 Trace 详情

**Files:**
- Modify: `static/debug.html`（JS 里加 selectTrace + renderDetail）

**Interfaces:**
- Consumes: `traces` 数组、当前点击的下标
- Produces: 函数 `selectTrace(index)`、`renderDetail()`（渲染 `#detail` + `#stats`）；把 `current` 设为选中的 trace

- [ ] **Step 1: 写 selectTrace + renderDetail**

在 `<script>` 里 `loadTraces()` 的上面或下面加：

```js
// 用户点列表某一项 → 选中并渲染详情
function selectTrace(index) {
  current = traces[index];
  // 高亮当前项
  document.querySelectorAll(".trace-item").forEach((el, i) => {
    el.classList.toggle("active", i === index);
  });
  renderDetail();
}

function renderDetail() {
  const detail = document.getElementById("detail");
  const stats = document.getElementById("stats");
  const empty = document.getElementById("empty");
  if (!current) return;

  empty.style.display = "none";

  // 统计卡
  const t = current.totals;
  stats.innerHTML =
    "<div><b>" + t.llm_calls + "</b> 轮LLM调用</div>" +
    "<div><b>" + t.tool_calls + "</b> 次工具调用</div>" +
    "<div><b>" + t.total_tokens + "</b> 总token</div>" +
    "<div><b>" + fmtTime(t.duration_ms) + "</b> 总耗时</div>";

  // 步骤详情（一次性全渲染，重放功能 Task 5 再做）
  detail.innerHTML = "";
  (current.steps || []).forEach((s, i) => renderStep(s, i));
}

// 把单步 step 渲染成一个 div，返回它（Task 5 重放会用到）
function renderStep(s, i) {
  const div = document.createElement("div");
  const dur = fmtTime(s.duration_ms);

  if (s.type === "llm_call") {
    div.className = "step llm";
    div.innerHTML =
      '<div class="head">💭 第 ' + (i + 1) + ' 步 · LLM 思考</div>' +
      '<div class="body">模型 ' + s.model + " · prompt " + s.prompt_tokens +
      " → completion " + s.completion_tokens + "</div>" +
      '<div class="dur">⏱ ' + dur + "</div>";
  } else {
    // tool_call
    div.className = "step tool";
    const result = (s.result || "").toString();
    // 结果里出现"未找到/失败/错误" → 标红
    if (/未找到|失败|错误|exception/i.test(result)) div.classList.add("bad");
    div.innerHTML =
      '<div class="head">🔧 ' + s.name + "</div>" +
      '<div class="body">参数 ' + JSON.stringify(s.args || {}) + "</div>" +
      '<div class="body">结果 ' + result.slice(0, 120) + "</div>" +
      '<div class="dur">⏱ ' + dur + "</div>";
  }
  return div;
}
```

- [ ] **Step 2: 验证详情**

刷新 `/debug` → 点左栏一条 → 右侧出现统计卡 + 所有步骤，LLM 思考是紫色边、工具是青色边、失败的标红。

- [ ] **Step 3: Commit**

```bash
git add static/debug.html
git commit -m "day22: Trace 详情渲染 + 统计卡"
```

**🧑‍🏫 教学点：**
- `classList.toggle("active", bool)`：加/去 class，用来做"高亮"
- `document.querySelectorAll`：按 CSS 选择器找一批元素
- 正则 `/未找到|失败|错误/i` 的 `.test()`：判断文本里有没有这些词，`i` = 忽略大小写
- 模板拼接字符串 `"<div>" + x + "</div>"`：把数据插进 HTML

---

### Task 5: 重放功能（播放/暂停/步进/速度）

**Files:**
- Modify: `static/debug.html`（JS 里加重放状态 + 控制逻辑）

**Interfaces:**
- Consumes: `current.steps`（渲染好的步骤数组，用全局 `stepEls` 保存）、按钮 `#playBtn/#pauseBtn/#prevBtn/#nextBtn`、下拉 `#speed`
- Produces: 全局 `stepEls`（已渲染的步骤 DOM 数组）、`curStep`（当前播放到第几步）、`timer`（定时器句柄）；函数 `play()` `pause()` `stepTo(n)`

- [ ] **Step 1: 改 renderDetail 保存步骤 DOM**

在 `renderDetail()` 里，把 `detail.innerHTML = ""` 后面改成**存起来**：

```js
  detail.innerHTML = "";
  stepEls = [];
  (current.steps || []).forEach((s) => {
    const div = renderStep(s, stepEls.length);
    stepEls.push(div);
    detail.appendChild(div);
  });
  curStep = -1;          // 还没开始播放
  stepTo(0);             // 先显示第 1 步
```

- [ ] **Step 2: 加重放逻辑 JS**

在 script 里加全局变量和播放控制：

```js
let stepEls = [];   // 已渲染的步骤 DOM 数组
let curStep = -1;   // 当前播放到的步骤下标
let timer = null;   // 定时器句柄

// 显示到第 n 步（0 起），高亮当前，自动滚动
function stepTo(n) {
  if (n < 0 || n >= stepEls.length) return;
  curStep = n;
  stepEls.forEach((el, i) => el.classList.toggle("now", i === n));
  stepEls[n].scrollIntoView({ behavior: "smooth", block: "center" });
}

// 播放：定时器每 interval ms 前进一步
function play() {
  pause();
  if (!stepEls.length) return;
  if (curStep >= stepEls.length - 1) stepTo(0);   // 播完了从头来
  const interval = parseInt(document.getElementById("speed").value, 10);
  timer = setInterval(() => {
    if (curStep < stepEls.length - 1) {
      stepTo(curStep + 1);
    } else {
      pause();                                    // 播完了自动停
    }
  }, interval);
}

function pause() {
  if (timer) { clearInterval(timer); timer = null; }
}

document.getElementById("playBtn").addEventListener("click", play);
document.getElementById("pauseBtn").addEventListener("click", pause);
document.getElementById("prevBtn").addEventListener("click", () => stepTo(curStep - 1));
document.getElementById("nextBtn").addEventListener("click", () => stepTo(curStep + 1));
```

- [ ] **Step 3: 验证重放**

刷新 → 点一条 → 第 1 步高亮 → 点 ▶ 播放：步骤逐条展开、高亮下移、自动滚动。试试 ⏮⏭ 和速度下拉。选一条步骤多的 Trace 效果最明显。

- [ ] **Step 4: Commit**

```bash
git add static/debug.html
git commit -m "day22: Trace 重放功能"
```

**🧑‍🏫 教学点：**
- `setInterval(函数, 毫秒)`：每 N 毫秒执行一次函数，返回一个"句柄"；`clearInterval(句柄)` 停止。这就是"播放"的本质
- `scrollIntoView`：让元素滚到可视区——实现"自动跟随"
- 播放状态用三个全局变量（stepEls/curStep/timer）管：DOM 存哪、播到哪、定时器在不在

---

### Task 6: 收尾——空状态/错误提示/刷新按钮

**Files:**
- Modify: `static/debug.html`

**Interfaces:**
- Consumes: 已有结构
- Produces: 无新接口；完善空状态显示、失败提示、手动刷新

- [ ] **Step 1: 补细节**

在 script 末尾加：

```js
// 手动刷新列表（页面底部加一个按钮调用它）
function refresh() { loadTraces(); }

// 列表为空时把空状态提示显示出来
//（在 loadTraces 的 renderList 里已处理 count；再把空提示补齐：）
document.getElementById("empty").style.display = "block";
```

在 HTML 的 controls 区加一个刷新按钮：

```html
<button onclick="refresh()">↻ 刷新</button>
```

在 sidebar 的 total 上面加：

```html
<button onclick="refresh()">↻ 刷新列表</button>
```

（挑一个位置放即可，别重复。）

- [ ] **Step 2: 最终验收**

对照设计文档验收标准逐条测：
1. `/debug` 打开，样式 TRAVERSO 风格
2. 用 Agent 聊一句 → 列表出现新记录
3. 点击记录 → 逐步展示，LLM/工具/失败区分明显
4. 播放按钮自动推进 + 高亮
5. 无数据时显示空状态提示

- [ ] **Step 3: Commit + 写 day22.md**

```bash
git add static/debug.html
git commit -m "day22: Debug 面板完成"
```

然后写 `learningdocs/day22.md`（学习记录 + 面试话术）。

**🧑‍🏫 教学点：** 空状态和刷新是"用户体验细节"——面试官不会直接问，但体现"我考虑过没数据怎么办"。面试讲面板时可以带一句"还处理了空状态和手动刷新"。

---

## 自审记录

- **Spec 覆盖**：列表 ✅(Task3)、详情 ✅(Task4)、重放+速度+高亮+滚动 ✅(Task5)、统计卡 ✅(Task4)、状态区分 llm/tool/失败 ✅(Task4)、空状态 ✅(Task6)、独立页+不动主前端 ✅(Task1-2)
- **占位符**：无 TBD/TODO，所有代码完整可粘贴
- **类型一致性**：`stepEls/curStep/timer` 在 Task5 定义后 Task5-6 使用；`fmtTime/renderStep/selectTrace/loadTraces` 跨 Task 签名一致
