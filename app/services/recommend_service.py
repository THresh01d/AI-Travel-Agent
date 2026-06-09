import httpx

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