import requests
import os
import json


DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"


def extract_travel_info(api_key, message):

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

    response = requests.post(
        DEEPSEEK_API_URL,
        headers=headers,
        json=data
    )

    result = response.json()

    ai_reply = result["choices"][0]["message"]["content"]

    return json.loads(ai_reply)

def generate_plan(
        api_key,
        city,
        days,
        budget,
        profile,
        spots
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

    请按Day1 Day2格式输出。
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

    response = requests.post(
        DEEPSEEK_API_URL,
        headers=headers,
        json=data
    )

    result = response.json()

    return result["choices"][0]["message"]["content"]