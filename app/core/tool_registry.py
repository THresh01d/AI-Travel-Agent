"""
工具注册表 — Agent 的"手和脚"

每个工具包含两部分：
1. schema    → 给 LLM 看的工具说明书（JSON Schema 格式）
2. handler   → 实际执行逻辑（async 函数）

和旧版 tool_router.py 的关键区别：
- 旧版：5 个粗粒度工具，选一个执行一条路走到底
- 新版：9 个细粒度工具，Agent 自己决定调哪些、调几次、什么顺序
"""

import json
import httpx
from app.database import load_profile, save_profile, load_history, save_history
from app.services.weather_service import get_weather

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

async def _handle_get_weather(api_key: str, args: dict, user_id: int) -> str:
    """查询某个城市未来几天天气"""
    city = args.get("city", "")
    days = args.get("days", 3)
    if not city:
        return "错误：未提供城市名"
    try:
        result = await get_weather(city, min(days, 7))
        return result
    except Exception as e:
        return f"天气查询失败：{e}"


async def _handle_search_spots(api_key: str, args: dict, user_id: int) -> str:
    """景点搜索——无 RAG 知识库，告诉 Agent 用自己的训练知识"""
    query = args.get("query", "")
    if not query:
        return "请提供搜索关键词"
    return f"未在本地知识库中找到关于'{query}'的信息。请根据你对该目的地的了解直接推荐景点和美食。"


async def _handle_get_user_profile(api_key: str, args: dict, user_id: int) -> str:
    """读取用户的旅行偏好"""
    try:
        profile = load_profile(user_id)
        if not profile:
            return "用户尚未设置任何偏好"
        return json.dumps(profile, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"读取用户偏好失败：{e}"


async def _handle_save_user_preference(api_key: str, args: dict, user_id: int) -> str:
    """保存一条用户偏好"""
    key = args.get("key", "")
    value = args.get("value", "")
    if not key:
        return "错误：未指定偏好类型"
    try:
        save_profile(user_id, {key: value})
        return f"已保存偏好：{key} = {value}"
    except Exception as e:
        return f"保存偏好失败：{e}"


async def _handle_get_travel_history(api_key: str, args: dict, user_id: int) -> str:
    """读取用户的历史旅行记录"""
    try:
        history = load_history(user_id)
        if not history:
            return "用户暂无旅行历史"
        # history 格式: [(destination, days, budget, created_time), ...]
        lines = []
        for h in history:
            lines.append(f"目的地：{h[0]}，天数：{h[1]}，预算：{h[2]}，时间：{h[3]}")
        return "\n".join(lines)
    except Exception as e:
        return f"读取旅行历史失败：{e}"


async def _handle_save_travel_history(api_key: str, args: dict, user_id: int) -> str:
    """保存一条旅行记录"""
    city = args.get("city", "")
    days = args.get("days", 0)
    budget = args.get("budget", 0)
    if not city:
        return "错误：未提供目的地城市"
    try:
        save_history(user_id, city, days, budget)
        return f"已保存旅行记录：{city}，{days}天，预算{budget}元"
    except Exception as e:
        return f"保存旅行记录失败：{e}"


async def _handle_generate_plan(api_key: str, args: dict, user_id: int) -> str:
    city = args.get("city", "")
    days = args.get("days", 3)
    budget = args.get("budget", 0)
    spots = args.get("spots", "")
    weather = args.get("weather", "")
    profile = args.get("profile", "")
    user_message = args.get("user_message", "")

    if not city:
        return "错误：未提供目的地城市"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    prompt = f"""请根据以下信息生成详细旅游攻略：

城市：{city}
天数：{days}
预算：{budget}
用户这次的原话：{user_message}
用户历史偏好（仅供参考，这次的要求优先）：{profile}

推荐景点：
{spots if spots else "暂无景点数据"}

天气预报：
{weather if weather else "暂无天气数据"}

请根据天气情况合理调整行程（如雨天建议室内景点，晴天建议户外活动）。
按Day1 Day2格式输出。"""

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                DEEPSEEK_API_URL,
                headers=headers,
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": "你是专业旅游规划师"},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"攻略生成失败：{e}"


async def _handle_recommend(api_key: str, args: dict, user_id: int) -> str:
    """根据用户偏好和历史，推荐目的地"""
    try:
        profile = load_profile(user_id)
        history = load_history(user_id)
    except Exception as e:
        return f"读取用户数据失败：{e}"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    prompt = f"""用户偏好：{profile if profile else "无"}
旅行历史：{history if history else "无"}

请推荐3个适合该用户的旅游目的地，并说明推荐理由。"""

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                DEEPSEEK_API_URL,
                headers=headers,
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": "你是专业旅行顾问"},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"推荐生成失败：{e}"


async def _handle_analyze(api_key: str, args: dict, user_id: int) -> str:
    """分析用户的旅行习惯和风格"""
    try:
        profile = load_profile(user_id)
        history = load_history(user_id)
    except Exception as e:
        return f"读取用户数据失败：{e}"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    prompt = f"""用户偏好：{profile if profile else "无"}
旅行历史：{history if history else "无"}

请分析该用户的旅行风格、预算水平、出行习惯，并给出未来旅行建议。"""

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                DEEPSEEK_API_URL,
                headers=headers,
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": "你是资深旅行分析师"},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"分析生成失败：{e}"


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询某个城市未来几天的天气预报。在规划旅行前应该先查天气，根据天气调整行程建议。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名，如：成都、北京、上海"},
                    "days": {"type": "integer", "description": "预报天数，默认3天，最多7天"},
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_spots",
            "description": "搜索本地知识库中的旅游信息。如果本地无结果，请根据你的训练知识直接推荐景点和美食。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词，如：成都美食、杭州景点"},
                    "top_k": {"type": "integer", "description": "返回结果数量，默认3"},
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_profile",
            "description": "获取当前用户的旅行偏好设置（如旅行风格、作息习惯、预算水平等）。在做推荐或规划前应该先了解用户偏好。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_user_preference",
            "description": "保存用户的一条旅行偏好。当用户表达喜好或习惯时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "偏好类型，如 travel_style、wake_up、preference"},
                    "value": {"type": "string", "description": "偏好具体内容，如 自由行、早起、喜欢美食"},
                },
                "required": ["key", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_travel_history",
            "description": "获取用户的历史旅行记录。了解用户去过哪里有助于推荐新目的地和避免重复。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_travel_history",
            "description": "保存一条旅行记录到历史中。在成功生成旅行攻略后调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "目的地城市"},
                    "days": {"type": "integer", "description": "旅行天数"},
                    "budget": {"type": "integer", "description": "旅行预算"},
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_travel_plan",
            "description": "生成最终的旅行攻略。应该在收集完天气、景点、用户偏好等信息后最后调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "目的地城市"},
                    "days": {"type": "integer", "description": "旅行天数"},
                    "budget": {"type": "integer", "description": "旅行预算"},
                    "spots": {"type": "string", "description": "从 search_spots 获取到的景点信息"},
                    "weather": {"type": "string", "description": "从 get_weather 获取到的天气信息"},
                    "profile": {"type": "string", "description": "从 get_user_profile 获取到的用户偏好"},
                    "user_message": {"type": "string", "description": "用户原始输入"},
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_destinations",
            "description": "根据用户偏好和历史，推荐适合的旅游目的地。用户说'推荐'、'适合去哪'时调用。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_travel_style",
            "description": "分析用户的旅行习惯、风格和偏好，给出个性化建议。用户要求分析自己时调用。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
]

TOOL_HANDLERS = {
    "get_weather": _handle_get_weather,
    "search_spots": _handle_search_spots,
    "get_user_profile": _handle_get_user_profile,
    "save_user_preference": _handle_save_user_preference,
    "get_travel_history": _handle_get_travel_history,
    "save_travel_history": _handle_save_travel_history,
    "generate_travel_plan": _handle_generate_plan,
    "recommend_destinations": _handle_recommend,
    "analyze_travel_style": _handle_analyze,
}


async def execute_tool(tool_name: str, args: dict, api_key: str, user_id: int) -> str:
    """
    执行一个工具并返回结果字符串。

    关键设计：所有工具的错误都在 handler 内部捕获，
    返回错误描述字符串而不是抛出异常。
    这样 Agent 看到错误后可以自己决定下一步（重试、换工具、或者跳过）。
    """
    handler = TOOL_HANDLERS.get(tool_name)
    if handler is None:
        return f"错误：未知工具 '{tool_name}'，可用工具：{list(TOOL_HANDLERS.keys())}"
    return await handler(api_key, args, user_id)
