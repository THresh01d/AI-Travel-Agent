import requests


def summarize_profile(
    api_key,
    profile
):

    url = "https://api.deepseek.com/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    prompt = f"""
    用户画像：

    {profile}

    请根据用户画像生成一句自然语言总结。

    不要返回JSON。
    直接回答即可。
    """

    data = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role":"system",
                "content":"你是旅行助手"
            },
            {
                "role":"user",
                "content":prompt
            }
        ]
    }

    response = requests.post(
        url,
        headers=headers,
        json=data
    )

    result = response.json()

    return result["choices"][0]["message"]["content"]

def summarize_history(
    api_key,
    history
):

    url = "https://api.deepseek.com/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    prompt = f"""
    旅行历史：

    {history}

    请根据历史记录生成自然语言总结。

    例如：

    您曾去过上海和成都。

    不要返回JSON。
    """

    data = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role":"system",
                "content":"你是旅行助手"
            },
            {
                "role":"user",
                "content":prompt
            }
        ]
    }

    response = requests.post(
        url,
        headers=headers,
        json=data
    )

    result = response.json()

    return result["choices"][0]["message"]["content"]