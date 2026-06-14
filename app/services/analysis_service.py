import httpx
import json


async def analyze_user(
    api_key,
    profile,
    history
):

    url = "https://api.deepseek.com/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    prompt = f"""
            用户画像：
            {profile}

            历史记录：
            {history}

            请分析：
            1. 用户旅行风格
            2. 用户预算水平
            3. 用户出行习惯
            4. 推荐未来旅游方向

            直接输出分析结果。
            """

    data = {
        "model":"deepseek-chat",
        "messages":[
            {
                "role":"system",
                "content":"你是资深旅行分析师"
            },
            {
                "role":"user",
                "content":prompt
            }
        ]
    }

    async with httpx.AsyncClient(timeout=30) as client:

        response = await client.post(
            url,
            headers=headers,
            json=data
        )

    result = response.json()

    return result["choices"][0]["message"]["content"]


async def analyze_user_stream(api_key, profile, history):
    """分析用户习惯——流式版本"""

    url = "https://api.deepseek.com/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    prompt = f"""
            用户画像：
            {profile}

            历史记录：
            {history}

            请分析：
            1. 用户旅行风格
            2. 用户预算水平
            3. 用户出行习惯
            4. 推荐未来旅游方向

            直接输出分析结果。
            """

    data = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": "你是资深旅行分析师"
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "stream": True
    }

    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream("POST", url, headers=headers, json=data) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    chunk_str = line[6:]
                    if chunk_str == "[DONE]":
                        break
                    chunk = json.loads(chunk_str)
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content