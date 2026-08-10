"""
可观测性 Trace —— 记录 Agent 每一步做了什么

    每次用户请求生成一个 Trace，记录：
    - 每轮 LLM 调用（model / token / 耗时）
    - 每个工具调用（工具名 / 参数 / 耗时 / 结果摘要）
    - 汇总统计（轮数 / 工具数 / 总 token / 总耗时）

    存储两处：
    1. logs/traces.jsonl —— 追加写入文件，可长期回溯
    2. 内存环形缓冲      —— 最近 50 条，供 Debug 面板实时查询
"""

import json
import time
import uuid
import os
import threading
from collections import deque


class Trace:
    """一次用户请求的完整执行记录"""

    def __init__(self, user_id: int, query: str):
        self.trace_id = uuid.uuid4().hex[:12]
        self.user_id = user_id
        self.query = query
        self.started_at = time.time()
        self.steps = []          # 每一步（llm_call / tool_call）
        self.totals = {
            "llm_calls": 0,
            "tool_calls": 0,
            "total_tokens": 0,
            "duration_ms": 0,
        }

    def add_llm_call(self, model: str, prompt_tokens: int, completion_tokens: int, duration_ms: int):
        """记录一轮 LLM 调用"""
        step = {
            "type": "llm_call",
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "duration_ms": duration_ms,
        }
        self.steps.append(step)
        self.totals["llm_calls"] += 1
        self.totals["total_tokens"] += prompt_tokens + completion_tokens

    def add_tool_call(self, name: str, args: dict, duration_ms: int, result_summary: str):
        """记录一次工具调用"""
        step = {
            "type": "tool_call",
            "name": name,
            "args": args,
            "duration_ms": duration_ms,
            "result": result_summary[:200],
        }
        self.steps.append(step)
        self.totals["tool_calls"] += 1

    def finish(self):
        """结束 Trace，写文件 + 进环形缓冲"""
        self.totals["duration_ms"] = int((time.time() - self.started_at) * 1000)

        record = {
            "trace_id": self.trace_id,
            "user_id": self.user_id,
            "query": self.query,
            "steps": self.steps,
            "totals": self.totals,
        }

        # 1. 追加写 JSONL 文件
        _append_to_file(record)

        # 2. 内存环形缓冲（供 Debug 面板）
        _ring_buffer.append(record)

        return record


# ============================================================
# 全局存储
# ============================================================

_ring_buffer = deque(maxlen=50)          # 最近 50 条
_buffer_lock = threading.Lock()
_LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "logs")


def _append_to_file(record: dict):
    """把一条 Trace 追加写入 logs/traces.jsonl"""
    try:
        os.makedirs(_LOG_DIR, exist_ok=True)
        path = os.path.join(_LOG_DIR, "traces.jsonl")
        line = json.dumps(record, ensure_ascii=False)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        # 日志写入失败不影响主流程
        print(f"[trace] 写入失败: {e}")


def get_recent_traces(limit: int = 50) -> list[dict]:
    """获取最近 N 条 Trace，供 Debug 面板查询（新→旧）"""
    with _buffer_lock:
        return list(_ring_buffer)[-limit:][::-1]
