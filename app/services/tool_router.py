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
                "required": ["destination"]
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


async def choose_tool(api_key, question, history=None):
    """用原生 Function Calling 让 AI 选择工具并提取参数，返回 (tool_name, args_dict)

    history: 对话历史列表，格式 [{"role": "user", "content": "..."}, ...]
    """

    url = "https://api.deepseek.com/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    messages = [
        {
            "role": "system",
            "content": """你是一个旅行助手。严格按以下规则选择工具：

1. 用户说了具体城市名（如"成都""上海"）+ 天数 → 选 travel，提取 destination 和 days
2. 用户请求推荐目的地（"推荐""适合去哪""什么地方好"）→ 选 recommend
3. 用户表达偏好/习惯（"我喜欢""我习惯""我讨厌"）→ 选 profile
4. 用户要求分析自己（"分析我的习惯""我的旅行风格"）→ 选 analysis
5. 用户问去过哪里（"历史""去过哪些"）→ 选 history

关键：只要用户说了具体城市名，就选 travel。不要选 recommend 或其他工具。"""
        },
    ]

    # 如果有历史对话，插入到 system prompt 和当前问题之间
    if history:
        messages.extend(history)

    messages.append({"role": "user", "content": question})

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
