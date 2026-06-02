Day6

学习内容：

1. 将save_profile()接入AI Travel Agent项目
2. 学习Python函数封装
3. 学习MySQL数据插入流程
4. 完成用户画像自动存储
5. 学习JSON解析与字典操作
6. 调试FastAPI与MySQL联动
7. 理解AI长期记忆实现原理

收获：

理解了AI应用中用户画像的保存流程。

掌握了：

* json.loads()
* dict.update()
* save_profile()
* SQL INSERT

理解了：
用户输入
↓
DeepSeek提取偏好
↓
Python解析
↓
MySQL存储
↓
生成个性化攻略

这一完整工作流程。

完成内容：
成功实现：
save_profile(profile)

自动保存用户偏好。

成功保存：
{
    "wake_up":"晚起",
    "travel_style":"自由行",
    "attraction_type":"小众景点"
}
到MySQL数据库。

测试结果：

输入：
我喜欢自由行
我喜欢晚起
我喜欢小众景点

再次输入：
我想去成都玩三天，预算1500

系统成功读取历史偏好并生成符合：
* 晚起
* 自由行
* 小众景点
特点的个性化旅游攻略。

项目进展：
AI Travel Agent已经具备：
* 城市知识库
* 用户画像
* MySQL存储
* 个性化攻略生成
核心能力。

