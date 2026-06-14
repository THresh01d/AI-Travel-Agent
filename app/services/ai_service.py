import os
import json
import httpx

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"


async def extract_travel_info(api_key, message):

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    messages = [
        {
            "role": "system",
            "content": """
        你是旅行信息和用户偏好提取助手。

        你的任务是提取：

        1.destination
        2.days
        3.budget
        4.profile
        关于4.profile例如：
                我喜欢自由行
                返回：
                {{
                    "travel_style":"自由行"
                }}
                我不喜欢早起
                返回：
                {{
                    "wake_up":"晚起"
                }}
                我钱不是很多
                返回:{{
                    "budget_level":"低"
                }}
                如果用户没有输入他想去什么地方而是只说了它的profile,比如:我喜欢自由行
                就返回:
                    {
                    "destination": null,
                    "days": null,
                    "budget": null,
                    "profile": {
                        "travel_style": "自由行"
                    }
                }
                如果没有偏好信息：
                返回：
                {{}}

        必须返回JSON格式。
        不要输出任何解释。
        """
        },
        {
            "role": "user",
            "content": message
        }
    ]

    data = {
        "model": "deepseek-chat",
        "messages": messages
    }

    async with httpx.AsyncClient(timeout=30) as client:

        response = await client.post(
            DEEPSEEK_API_URL,
            headers=headers,
            json=data
        )

    result = response.json()

    ai_reply = result["choices"][0]["message"]["content"]

    return json.loads(ai_reply)

async def generate_plan(
        api_key,
        city,
        days,
        budget,
        profile,
        spots,
        weather: str = ""
):

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    plan_prompt = f"""
    请根据以下信息生成详细旅游攻略：

    城市：{city}
    天数：{days}
    预算：{budget}
    用户偏好：{profile}

    推荐景点：
    {spots}

    天气预报：
    {weather if weather else "暂无天气数据"}

    请根据天气情况合理调整行程（如雨天建议室内景点，晴天建议户外活动）。
    按Day1 Day2格式输出。
    """


    data = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": "你是专业旅游规划师"
            },
            {
                "role": "user",
                "content": plan_prompt
            }
        ]
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            DEEPSEEK_API_URL,
            headers=headers,
            json=data
        )

    result = response.json()

    return result["choices"][0]["message"]["content"]

async def generate_plan_stream(api_key, city, days, budget, profile, spots, weather=""):
    """生成攻略——流式版本，逐字返回"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    plan_prompt = f"""
    请根据以下信息生成详细旅游攻略：

    城市：{city}
    天数：{days}
    预算：{budget}
    用户偏好：{profile}

    推荐景点：
    {spots}

    天气预报：
    {weather if weather else "暂无天气数据"}

    请根据天气情况合理调整行程。按Day1 Day2格式输出。
    """

    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是专业旅游规划师"},
            {"role": "user", "content": plan_prompt}
        ],
        "stream": True   # ← 关键：开启流式
    }

    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream("POST", DEEPSEEK_API_URL, headers=headers, json=data) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    chunk_str = line[6:]     # 去掉 "data: " 前缀
                    if chunk_str == "[DONE]":
                        break
                    chunk = json.loads(chunk_str)
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content       # ← yield，不 return
