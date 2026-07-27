"""
流程：
  用户输入
    ↓
  [while 循环开始]
    ↓
  调用 DeepSeek（带工具定义）
    ↓
  DeepSeek 返回 tool_calls? ──是──→ 执行工具 → 把结果追加到对话 → 回到循环开头
    ↓ 否
  返回文本内容 → 结束
"""

import json
import httpx
from app.core.tool_registry import TOOL_DEFINITIONS, execute_tool

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
MAX_ITERATIONS = 5  


# ReAct 模式的 System Prompt
# 这是教 Agent "怎么思考"的核心——不是教它选哪个工具，而是教它解决问题的流程
SYSTEM_PROMPT = """你是一个智能旅行规划助手。你需要通过多步推理来帮助用户。

## 工作流程

1. **理解需求**：用户想要什么？规划旅行、对比城市、推荐目的地、还是分析习惯？
2. **收集信息**：你需要哪些数据？天气？景点？ 用户偏好？历史记录？
3. **调用工具**：一次可以调用多个工具（会并行执行），拿到结果后评估是否足够
4. **综合回答**：所有必要信息齐全后，生成最终回答

## 重要规则

- **先收集信息，再下结论**。不要跳过工具调用直接回答
- 如果用户说了城市名+天数，你应该：查天气 → 搜景点 → 读偏好 → 生成攻略
- 如果结果不够（比如天气数据不全），可以再调一次工具
- 每次调用工具前，简单说明你为什么要调这个工具
- 所有回复使用中文
- 攻略按 Day1、Day2... 格式输出
- **如果用户没有说具体城市**（只说"想去海边""想看雪""预算2000"），你应该先调用 recommend_destinations 来推荐适合的城市，而不是直接搜景点或查天气
- 如果推荐结果回来了，选一个最合适的城市，再查天气+搜景点+生成攻略
- 如果某个工具返回空结果或错误，不要反复重试同一个工具，换个思路或者直接用已有的信息回答用户


## 可用工具

你有以下工具可以使用。每个工具提供不同类型的信息，你需要自己决定调用的顺序和组合。"""


async def run_agent_loop(
    api_key: str,
    user_message: str,
    user_id: int,
    conversation_history: list[dict] | None = None
):
    """
    Agent 主循环 — 异步生成器，yield 结构化事件。

    参数：
        api_key: DeepSeek API Key
        user_message: 用户当前输入
        user_id: 当前登录用户 ID
        conversation_history: 之前的对话历史，格式 [{"role": "...", "content": "..."}]

    yield 的事件类型：
        {"type": "thinking"}              → Agent 开始新一轮思考
        {"type": "tool_call", ...}        → Agent 决定调用某个工具
        {"type": "tool_result", ...}      → 工具执行完毕
        {"type": "content", "text": "..."} → 最终文本（流式逐字）
        {"type": "done", "stats": {...}}  → 对话结束，附带统计
    """
    # ---- 1. 构建消息列表 ----
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # 如果有历史对话，插入 system prompt 和当前问题之间
    if conversation_history:
        messages.extend(conversation_history)

    messages.append({"role": "user", "content": user_message})

    # ---- 2. 统计信息 ----
    stats = {
        "iterations": 0,
        "tool_calls": 0,
        "tools_called": [],
        "total_tokens": 0,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # ---- 3. ReAct 主循环 ----
    # 这就是你把"路由器"变成"Agent"的地方：不是选一个工具，而是在循环里反复调用 LLM
    for iteration in range(1, MAX_ITERATIONS + 1):
        stats["iterations"] = iteration

        # 通知前端：Agent 开始思考
        yield {"type": "thinking", "iteration": iteration}

        # ---- 3a. 调用 DeepSeek（带工具定义）----
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    DEEPSEEK_API_URL,
                    headers=headers,
                    json={
                        "model": "deepseek-chat",
                        "messages": messages,
                        "tools": TOOL_DEFINITIONS,
                    }
                )
            result = response.json()
        except Exception as e:
            yield {"type": "content", "text": f"抱歉，AI 服务暂时不可用：{e}"}
            yield {"type": "done", "stats": stats}
            return

        # 记录 token 消耗
        if "usage" in result:
            stats["total_tokens"] += result["usage"].get("total_tokens", 0)

        choice = result["choices"][0]
        message = choice["message"]

        # ---- 3b. 判断：LLM 想调工具还是返回文本？----

        # 情况1：LLM 返回了 tool_calls → 执行工具，继续循环
        if message.get("tool_calls"):
            # 把 LLM 的 tool_call 请求追加到对话历史
            messages.append({
                "role": "assistant",
                "content": message.get("content") or "",
                "tool_calls": message["tool_calls"]
            })

            # 逐个执行工具
            for tc in message["tool_calls"]:
                tool_name = tc["function"]["name"]

                # 安全解析参数
                try:
                    args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    args = {}

                stats["tool_calls"] += 1
                stats["tools_called"].append(tool_name)

                # 通知前端：正在调工具
                yield {
                    "type": "tool_call",
                    "name": tool_name,
                    "args": args,
                }

                # 执行工具
                tool_result = await execute_tool(tool_name, args, api_key, user_id)

                # 通知前端：工具执行完毕
                yield {
                    "type": "tool_result",
                    "name": tool_name,
                    "summary": tool_result[:200] + ("..." if len(tool_result) > 200 else ""),
                }

                # 把工具结果追加到对话历史
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": tool_result,
                })

            # 这一轮的工具都执行完了，回到循环开头让 LLM 重新评估
            continue

        # 情况2：LLM 返回了纯文本 → 对话结束
        if message.get("content"):
            content = message["content"]
            # 因为是非流式调用，整段返回
            yield {"type": "content", "text": content}
            yield {"type": "done", "stats": stats}
            return

        # 情况3：既没有 tool_calls 也没有 content → 异常，安全退出
        yield {"type": "content", "text": "抱歉，我暂时无法处理这个请求，请换个方式试试。"}
        yield {"type": "done", "stats": stats}
        return

    # ---- 4. 超过最大循环次数 ----
    yield {
        "type": "content",
        "text": f"抱歉，这个请求比较复杂，我在 {MAX_ITERATIONS} 轮思考后仍未能完成。请尝试用更简单的方式描述您的需求。"
    }
    yield {"type": "done", "stats": stats}
