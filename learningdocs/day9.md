# Day10：旅行历史记录系统

## 学习内容

1. 设计 travel_history 数据表
2. 学习用户与历史记录的关联关系
3. 使用外键（Foreign Key）关联 users 表
4. 实现 save_history() 函数
5. 实现 load_history() 函数
6. 实现旅行记录自动保存
7. 新增 GET /history GET /profile接口
8. 实现历史旅行记录查询

## 完成内容

### 创建 travel_history 表
CREATE TABLE travel_history(
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    destination VARCHAR(50),
    days INT,
    budget INT,
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

### 测试插入数据

INSERT INTO travel_history
(user_id,destination,days,budget)
VALUES
(1,'成都',3,1500);

成功写入数据库。

### 实现 save_history()

当用户生成旅行攻略时：
成都 3天 1500元

自动保存到 travel_history 表中。

### 实现 load_history()
根据 user_id 查询当前用户历史旅行记录：
load_history(user_id)

### 新增接口
GET /history:
用于查看当前用户所有历史旅行记录。

### 接口测试成功

返回结果：

```json
{
    "user_id": 1,
    "history": [
        {
            "destination": "上海",
            "days": 3,
            "budget": 2000,
            "created_time": "2026-06-05 00:09:59"
        },
        {
            "destination": "成都",
            "days": 3,
            "budget": 1500,
            "created_time": "2026-06-05 00:05:31"
        }
    ]
}
说明历史记录保存与读取功能全部正常。


## 收获

理解了：

* 用户表（users）
* 用户画像表（user_profile）
* 旅行历史表（travel_history）

三者之间的数据关系。

掌握了：

* 外键的使用方法
* MySQL 多表关联思想
* 历史数据持久化存储
* FastAPI GET 接口开发
理解了为什么 AI Agent 需要长期记忆能力。
---

## 当前项目能力

已实现：
* 用户注册
* 用户登录
* 用户画像提取
* 用户画像持久化
* 旅行攻略生成
* 旅行历史记录保存
* 旅行历史记录查询

项目已经具备基础 AI Travel Agent 功能。