Day3：结构化数据提取
学习内容
JSON格式
json.loads()
Prompt工程
信息抽取
完成内容

设计Prompt：

要求AI只返回JSON格式。

输入：

我想去成都玩3天预算3000

输出：

{
    "destination":"成都",
    "days":3,
    "budget":3000
}
遇到的问题

AI偶尔返回解释文字。

解决方法

加强Prompt约束：

必须返回JSON格式
不要输出任何解释
收获

理解：

AI输出文本

↓

json.loads()

↓

Python字典

转换过程。