import json
import httpx

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "travel",
            "description": "用户想规划一次旅行，需要生成旅游攻略",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {"type": "string", "description": "目的地城市"},
                    "days": {"type": "integer", "description": "旅行天数"},
                    "budget": {"type": "integer", "description": "旅行预算"},
                    "preference": {"type": "string", "description": "用户的旅行偏好"},
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "profile",
            "description": "用户想表达或查询自己的旅行偏好和习惯",
            "parameters": {
                "type": "object",
                "properties": {
                    "travel_style": {"type": "string", "description": "旅行风格，如自由行、跟团游"},
                    "wake_up": {"type": "string", "description": "作息习惯，如早起、晚起"},
                    "preference": {"type": "string", "description": "其他偏好描述"},
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "history",
            "description": "用户想查看自己的历史旅行记录",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recommend",
            "description": "用户想让AI推荐适合的旅游目的地",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analysis",
            "description": "用户想让AI分析自己的旅行习惯和风格",
            "parameters": {"type": "object", "properties": {}}
        }
    },
]


async def choose_tool(api_key, question):
    """用原生 Function Calling 让 AI 选择工具并提取参数，返回 (tool_name, args_dict)"""

    url = "https://api.deepseek.com/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    messages = [
        {"role": "system", "content": "你是一个旅行助手。根据用户的话选择合适的工具。"},
        {"role": "user", "content": question}
    ]

    data = {
        "model": "deepseek-chat",
        "messages": messages,
        "tools": TOOLS,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, headers=headers, json=data)

    result = response.json()
    message = result["choices"][0]["message"]


    if "tool_calls" in message:
        tool_call = message["tool_calls"][0]
        tool_name = tool_call["function"]["name"]
        args = json.loads(tool_call["function"]["arguments"])
        return tool_name, args
    else:
        return "travel", {}
