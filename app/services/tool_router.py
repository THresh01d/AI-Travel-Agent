import json
import httpx


async def choose_tool(api_key, question):

    url = "https://api.deepseek.com/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    messages = [
        {
            "role": "system",
            "content": """
        你是一个工具选择器。

        可选工具：

        history
        当用户询问：
        - 去过哪些地方
        - 历史旅行记录
        - 回顾旅程

        返回：
        {
            "tool":"history"
        }

        profile
        当用户询问：
        - 我的偏好
        - 我的旅行风格
        - 我的习惯

        返回：
        {
            "tool":"profile"
        }

        travel
        当用户询问：
        - 帮我规划旅游
        - 帮我做攻略
        - 成都三日游
        - 上海两天怎么玩

        返回：
        {
            "tool":"travel"
        }

        recommend
        当用户询问：
        -推荐城市
        -适合去哪玩
        -推荐旅游地点
        -下次去哪旅游

        返回：
        {
            "tool":"recommend"
        }

        analysis
        如果用户询问：
        分析我的旅行习惯
        分析我的旅游偏好
        总结我的出行风格
        我的旅行画像是什么

        返回：
        {
            "tool":"analysis"
        }

        不要输出解释。
        """
        },
        {
            "role": "user",
            "content": question
        }
    ]

    data = {
        "model": "deepseek-chat",
        "messages": messages
    }

    async with httpx.AsyncClient(timeout=30) as client:

        response = await client.post(
            url,
            headers=headers,
            json=data
        )

    result = response.json()

    content = result["choices"][0]["message"]["content"]

    return json.loads(content)