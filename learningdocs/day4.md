Day4：旅游攻略生成 + 用户画像
学习内容
两次AI调用
Prompt链式调用
用户画像(User Profile)
Python字典存储
完成内容

第一步：

提取用户信息：
{
    "destination":"上海",
    "days":3,
    "budget":3000
}

第二步：
根据提取结果生成完整攻略。

实现：
用户输入
↓
AI提取
↓
程序处理
↓
AI生成攻略

双阶段工作流。

用户画像功能

实现：
user_profile = {}

支持记录：
{
    "wake_up":"晚起",
    "travel_style":"自由行"
}

用户输入：
我喜欢自由行
保存偏好。
之后输入：
我想去上海玩3天
攻略自动参考用户偏好。

遇到的问题
问题1：
profile字段读取错误

解决：
profile = parsed_data.get(
    "profile",
    {}
)

问题2：
用户画像与本次输入混淆

解决：
区分：parsed_data和user_profile

收获
理解：
短期记忆的本质：
user_profile.update(profile)

理解：
AI Agent并不是魔法。很多能力本质是：
AI
+
Prompt
+
程序逻辑
+
数据存储

共同实现。