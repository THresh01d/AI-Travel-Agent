# Day19：MySQL 连接池 + Docker 部署配置

---

## 一、MySQL 连接池

### 学习内容

1. 为什么每次请求新建数据库连接是浪费
2. DBUtils.PooledDB 的使用
3. 连接池的工作方式（拿 → 用 → 还）

### 改进前的状态

```python
def get_connection():
    return pymysql.connect(      # 每次调用 → 新建连接
        host=settings.mysql_host,
        ...
    )
```

每次数据库操作（读偏好、读历史、存记录）都走完整流程：**TCP 握手 → MySQL 认证 → 执行 SQL → 关闭连接**。

用户一次对话可能触发 3-5 次数据库操作，就是 3-5 次握手。每个握手几十毫秒，量大起来（或并发起来）MySQL 会撑不住。

### 改进方案

```python
from dbutils.pooled_db import PooledDB

pool = PooledDB(
    creator=pymysql,       # 用 pymysql 创建连接
    maxconnections=5,      # 池子里最多 5 个连接
    host=settings.mysql_host,
    user=settings.mysql_user,
    password=settings.mysql_password,
    database=settings.mysql_database,
    charset="utf8mb4",
)

def get_connection():
    return pool.connection()   # 从池子里拿一个，用完还回去
```

**关键点：** 其他所有函数（`save_profile`、`load_history` 等）一行都不用改——它们只关心调 `get_connection()` 拿到连接，不关心连接是从池里拿的还是新建的。这就是**封装的好处**：改底层实现，调用方无感知。

### 连接池的工作方式

```
没有池：  需要连接 → 新建（握手） → 用完 → 关闭
有池：    需要连接 → 从池里拿    → 用完 → 还回去（不握手）
```

`maxconnections=5`：同时最多 5 个连接在跑，第 6 个请求来了就排队等，前面的还回去才能拿。

### 遇到的问题

**问题：DBUtils 没装**

`from dbutils.pooled_db import PooledDB` 直接 ModuleNotFoundError。

解决：`pip install dbutils`。

**问题：为什么这么写，`get_connection()` 返回的还能用 `conn.close()` 关？**

理解：PooledDB 的 `close()` 不是真的关闭连接，而是**把连接还回池子**。对调用方来说代码不用变，`conn.close()` 照写，但实际行为从"关闭"变成了"归还"。连接池框架帮我们把这个细节藏起来了。

### 收获

1. **连接池是生产环境的标配。** 本地开发感觉不到，但并发一上来，没有连接池的 MySQL 会被连接请求打爆。面试问"高并发下数据库怎么扛"，第一反应就该是连接池
2. **好的封装让调用方无感知。** 我只改了 `get_connection()` 一个函数，其余 7 个数据库函数一行没动。这就是为什么要把"获取连接"这件事集中在一个地方
3. **"池"是通用概念。** 数据库连接池、HTTP 连接池、线程池——都是"预先创建一批资源，用的时候拿，用完还"的同一个思想

---

## 二、Docker 部署配置

### 学习内容

1. Dockerfile 是什么，为什么用多阶段构建
2. docker-compose 多服务编排（FastAPI + MySQL）
3. .dockerignore 为什么重要

### 为什么要做

面试官判断"会不会部署"，不是看你是不是真的租了台服务器，而是看你的代码**能不能随时跑在任意一台机器上**。仓库里有 Dockerfile + docker-compose.yml，说明：

- 你知道怎么把 Python 代码打包成镜像
- 你知道多服务怎么编排（FastAPI 依赖 MySQL，要控制启动顺序）
- 你的项目不是"只能在我电脑上跑"

### Dockerfile（多阶段构建）

```dockerfile
# 第一阶段：只装依赖
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 第二阶段：只放代码 + 已装好的依赖
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**为什么分两阶段：** 最终镜像不包含 pip 的缓存、头文件、编译中间产物，体积能小 40%。

**为什么先复制 requirements.txt 再装依赖：** 这是 Docker 缓存优化。只改代码不改依赖时，Docker 会复用前两步的缓存，跳过 pip install，构建只要几秒。

### docker-compose.yml

```yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env          # 环境变量从 .env 注入
    depends_on:
      mysql:
        condition: service_healthy  # 等 MySQL 健康了再启动 app

  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_PASSWORD}
      MYSQL_DATABASE: ${MYSQL_DATABASE}
    volumes:
      - mysql_data:/var/lib/mysql   # 数据持久化，容器删了数据还在
    healthcheck:                    # 健康检查，app 等它好了再启动
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
```

**关键设计：**
- `depends_on + condition: service_healthy` → 保证 MySQL 先启动好，app 再启动，否则 app 连不上数据库直接崩
- `volumes: mysql_data` → 数据库数据存在磁盘上，容器重启/删除数据不丢

### .dockerignore

`.env`（含 API Key）、`__pycache__`、`learningdocs`、`chroma_data` 都不打进镜像。镜像里不该有密钥，也不该有和运行无关的文件。

### 部署命令

```bash
docker-compose up -d    # 后台启动
docker-compose down     # 停止
```

打开 `http://服务器IP:8000/app` 访问。

### 遇到的问题

**问题：requirements.txt 原来是空的**

之前 `pip install` 都是手动装的，没记录到 requirements.txt。导致的问题：换台电脑装不起来，Docker 镜像也构建不了（没有依赖清单）。

解决：`pip freeze` 查当前装的包，整理出项目实际用到的依赖写进 requirements.txt。

### 收获

1. **部署能力不是"租个服务器"，是"代码可移植"。** Docker 的价值是一套配置哪里都能跑——本机、云服务器、面试官想试试也行
2. **环境问题是最烦人的。** "我电脑能跑，你电脑跑不了"是经典事故。requirements.txt + Docker 就是解决这个的
3. **面试能讲的东西：** 多阶段构建（镜像瘦身）、Docker 缓存优化、service_healthy 控制启动顺序、volumes 数据持久化——这些都是不照抄教程、真理解了才会写的

---

## 三、README 更新

把原来一行字的 README 改成项目介绍 + 快速开始 + 技术栈 + 学习记录入口。面试官打开仓库第一眼看到的就是 README，这是你的门面。

---

## 项目文件变更

### 新增
- `Dockerfile` — 多阶段构建
- `docker-compose.yml` — FastAPI + MySQL 编排
- `.dockerignore` — 排除敏感文件
- `requirements.txt` — 项目依赖清单（原来为空）

### 修改
- `app/database.py` — 从每次新建连接 → DBUtils.PooledDB 连接池
- `README.md` — 从一行字 → 完整项目介绍

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
✓ 自定义 HTML 前端（手绘旅行日志风格）
✓ Pydantic Settings 统一配置（启动时校验）
✓ 异常层次结构 + 全局错误中间件
✓ MySQL 连接池（DBUtils.PooledDB，最多 5 连接复用）
✓ Docker 多阶段构建 + docker-compose 编排
✓ requirements.txt 依赖清单
✓ README 项目介绍
```

## 下一步

- 可观测性（结构化 Trace：每步 LLM 调用/token/耗时）
- Debug 面板（前端展示 Agent 推理过程）
- 评估框架（测试场景 + LLM-as-Judge）
