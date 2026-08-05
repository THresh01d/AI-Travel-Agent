# Day20：对话历史持久化——从内存到 MySQL

---

## 一、为什么要做

### 改进前的状态

`conversation.py` 用 Python 内存 dict 存对话历史：

```python
# {user_id: [{"role": "user", "content": "..."}, ...]}
_history: dict[int, list[dict]] = {}
```

问题：

| 问题 | 后果 |
|------|------|
| 服务重启 → 内存清空 | 用户多轮对话的记忆全部丢失 |
| 多 worker 部署 → 每个进程各一份 | 请求落到不同进程，记忆互相不认识 |
| 数据不落盘 | 没有任何持久化，纯运行时状态 |

**本质：Agent 的"短期记忆"应该是可持久化的，不是进程内的临时变量。**

面试官必问的一句："你的多轮对话记忆怎么存的？重启会丢吗？"——答"存在内存 dict 里"是明显的架构缺陷。

### 为什么做

1. 对话记忆是 Agent 的核心能力之一（用户画像/历史已经是数据库存的，唯独对话不是）
2. 这是"能上线"和"demo"的分水岭——demo 可以丢记忆，生产不能
3. 改动小、收益大：一个函数改实现，接口不变，调用方零感知

---

## 二、数据表设计

```sql
CREATE TABLE conversation_messages(
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    role VARCHAR(10),          -- 'user' 或 'assistant'
    content TEXT,
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id),
    INDEX idx_user_time (user_id, id)
);
```

### 设计要点

| 字段 | 为什么 |
|------|--------|
| `id` 自增主键 | 天然的对话顺序：id 越大越新 |
| `role` VARCHAR(10) | 区分 user / assistant，长度限制防滥用 |
| `content` TEXT | 攻略可能很长，用 TEXT 不设限 |
| `user_id` 外键 | 关联 users 表，保证用户存在性 |
| `INDEX (user_id, id)` | 复合索引，查询"某用户最近 N 条"走索引不扫全表 |

**关键认知：持久化不是"全删重建"，是"全存 + 取最近"。** 数据库不删旧消息，`get_history` 只取最近 10 条——这恰好就是长期记忆的正确姿势：全都留着，喂给 LLM 的只用最近的。

---

## 三、conversation.py 改造

### 改造前

```python
_history = {}

def add_message(user_id, role, content):
    if user_id not in _history:
        _history[user_id] = []
    _history[user_id].append({"role": role, "content": content})
    if len(_history[user_id]) > 10:
        _history[user_id] = _history[user_id][-10:]

def get_history(user_id):
    return _history.get(user_id, [])
```

### 改造后

```python
from app.database import get_connection

def add_message(user_id, role, content):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        sql = """
        INSERT INTO conversation_messages (user_id, role, content)
        VALUES (%s, %s, %s)
        """
        cursor.execute(sql, (user_id, role, content))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def get_history(user_id, limit=10):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        sql = """
        SELECT role, content
        FROM conversation_messages
        WHERE user_id = %s
        ORDER BY id DESC
        LIMIT %s
        """
        cursor.execute(sql, (user_id, limit))
        rows = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]
```

### 三个设计决策

1. **`try/finally` 保证资源释放**：无论 SQL 成功还是失败，连接都会归还连接池。之前 `conn.close()` 在 try 外面，如果 SQL 抛异常连接就漏关了
2. **`ORDER BY id DESC LIMIT %s` + `reversed()`**：取最近 limit 条（倒序）再反转成正序。不反转的话，Agent 看到的对话是反的
3. **返回格式完全不变**：还是 `[{"role": ..., "content": ...}]`，`agent_loop.py` 直接喂给 DeepSeek，`main.py` 一行都不用改

### 为什么接口不变

`main.py` 调用：

```python
history = get_history(user_id)            # 拿历史
add_message(user_id, "user", req.message)  # 存用户消息
```

调用方只依赖函数签名，不依赖"它怎么实现"。把内存换成数据库，是**改内部实现不动接口**——这就是封装的收益，也是重构能零风险进行的原因。

---

## 四、遇到的问题

### 问题 1：外键约束失败

```
IntegrityError: Cannot add or update a child row:
a foreign key constraint fails ...
conversation_messages FK(user_id) REFERENCES users(id)
```

**原因**：测试用了 `user_id=1`，但 `users` 表里根本没有 id=1 的用户（真实用户是 4、5、6、7）。

**解决**：先 `SELECT id FROM users` 看真实用户，改用存在的 user_id 测试。

**收获**：外键不是摆设——它强制保证"对话一定属于一个真实用户"。这是数据完整性的保障，不是麻烦。

### 问题 2：终端中文乱码

```
'�ɶ���������'   # 应该是 '成都三日游'
```

**原因**：Windows 终端 GBK 编码显示 UTF-8 输出。

**解决**：不是程序问题，数据在数据库里是对的。用 `SELECT` 在 MySQL 客户端看就是正常的。开发时不必纠结终端显示。

---

## 五、持久化验证

模拟"重启"场景——两个完全独立的 Python 进程：

```
进程 A：add_message(4, 'user', '我想去大理')
        add_message(4, 'assistant', '大理攻略如下...')
        → 读回 2 条 ✓

=== 模拟服务重启 ===

进程 B（全新进程，无任何内存状态）：
        get_history(4)
        → 读回 2 条 ✓  ← 关键：数据来自数据库，不是内存
```

**两个进程读到相同数据 = 持久化生效。**

---

## 六、收获

1. **短期记忆也值得持久化**。Agent 的记忆分为：长期（用户画像/旅行历史，已经入库）和短期（对话上下文）。两者都应该落库，只是用途不同
2. **索引设计有讲究**。`(user_id, id)` 复合索引让"某用户的最近对话"查询是索引命中，数据量大了也快
3. **改内部实现不动接口是重构的安全带**。因为 `get_history` 的返回格式没变，`agent_loop.py`、`main.py` 完全不用动，重构零风险
4. **`try/finally` 比 `try/except` 更适合资源释放**。`finally` 无论成功失败都会执行——关闭数据库连接就该用它

---

## 当前项目能力

```
✓ 用户注册/登录（bcrypt 密码哈希）
✓ JWT Bearer Token 认证（24 小时过期）
✓ ReAct Agent Loop（多轮推理 + 多工具编排）
✓ 原生 Function Calling（DeepSeek tools 参数）
✓ 9 个细粒度工具（Agent 自主决定调用顺序）
✓ 用户画像自动提取 + 存储 + 总结
✓ 旅行历史智能存储
✓ 实时天气 API（Open-Meteo，免费无需 Key）
✓ SSE 结构化事件流
✓ async/await 异步全链路
✓ 自定义 HTML 前端
✓ Pydantic Settings 统一配置（启动时校验）
✓ 异常层次结构 + 全局错误中间件
✓ MySQL 连接池（DBUtils.PooledDB）
✓ Docker 多阶段构建 + docker-compose 编排
✓ 对话历史持久化（conversation_messages 表）
```

## 下一步

- 可观测性（结构化 Trace：每步 LLM 调用/token/耗时）
- Debug 面板（前端展示 Agent 推理过程）
- httpx 共享客户端接入（http_client.py 还没被真正使用）
