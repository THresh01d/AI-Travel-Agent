import httpx
import json

async def recommend_city(
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

        历史旅行记录：

        {history}

        请推荐3个适合他的旅游城市。

        说明原因。

        不要返回JSON。
        """

    data = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role":"system",
                "content":"你是专业旅行顾问"
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


async def recommend_city_stream(api_key, profile, history):
    """推荐城市——流式版本"""

    url = "https://api.deepseek.com/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    prompt = f"""
        用户画像：

        {profile}

        历史旅行记录：

        {history}

        请推荐3个适合他的旅游城市。

        说明原因。

        不要返回JSON。
        """

    data = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": "你是专业旅行顾问"
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