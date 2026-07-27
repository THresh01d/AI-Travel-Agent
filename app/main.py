from fastapi import FastAPI
from fastapi import Depends
from pydantic import BaseModel
from dotenv import load_dotenv
import json as json_lib
import os


from app.database import load_profile, load_history
from app.database import create_user, get_user_by_username

from app.services.auth_service import create_token
from app.services.auth_service import verify_token
from app.services.dependency import get_current_user
from app.services.auth_service import hash_password
from app.services.auth_service import verify_password
from app.services.conversation import add_message, get_history
from app.core.agent_loop import run_agent_loop

from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    yield
    # 关闭时执行（你暂时不需要做什么，留空）

app = FastAPI(lifespan=lifespan)

# CORS —— 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str

class RegisterRequest(BaseModel):
    username: str
    password: str

class TokenRequest(BaseModel):
    token: str

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")


@app.get("/")
def home():
    return {"message": "AI Travel Agent Running"}

@app.post("/register")
def register(req: RegisterRequest):

    user = get_user_by_username(
        req.username
    )

    if user:
        return {
            "message": "用户名已存在"
        }

    create_user(
        req.username,
        hash_password(req.password)
    )

    return {
        "message": "注册成功"
    }

@app.post("/login")
def login(req: RegisterRequest):

    user = get_user_by_username(
        req.username
    )

    if not user:
        return {
            "message": "用户不存在"
        }

    if not verify_password(req.password, user[2]):
        return {
            "message": "密码错误"
            }

    token = create_token(
        user[0]
    )

    return {
        "message": "登录成功",
        "token": token
    }

@app.post("/agent")
async def agent(
    req: ChatRequest,
    user_id: int = Depends(get_current_user)
):
    """Agent 端点（非流式）—— Agent Loop 驱动，Agent 自主决定调用哪些工具"""
    if user_id is None:
        return {"message": "token无效"}

    history = get_history(user_id)
    add_message(user_id, "user", req.message)

    # 收集 Agent Loop 的所有事件，提取最终回答
    final_answer = ""
    stats = {}
    async for event in run_agent_loop(
        DEEPSEEK_API_KEY, req.message, user_id, history
    ):
        if event["type"] == "content":
            final_answer = event["text"]
        elif event["type"] == "done":
            stats = event.get("stats", {})

    add_message(user_id, "assistant", final_answer)
    return {"answer": final_answer, "stats": stats}


@app.post("/agent/stream")
async def agent_stream(
    req: ChatRequest,
    user_id: int = Depends(get_current_user)
):
    """Agent 流式端点 — SSE 实时输出 Agent 的思考→调工具→观察→再思考全过程"""
    if user_id is None:
        return {"message": "token无效"}

    history = get_history(user_id)
    add_message(user_id, "user", req.message)

    async def generate():
        full_answer = ""
        async for event in run_agent_loop(
            DEEPSEEK_API_KEY, req.message, user_id, history
        ):
            # 把每个事件序列化为 SSE 格式
            yield f"data: {json_lib.dumps(event, ensure_ascii=False)}\n\n"

            if event["type"] == "content":
                full_answer = event["text"]

        # 流结束后保存对话
        if full_answer:
            add_message(user_id, "assistant", full_answer)

    return StreamingResponse(generate(), media_type="text/event-stream")


   

@app.post("/history")
def history(
    user_id: int = Depends(get_current_user)
):

    print("history user_id=", user_id)

    if user_id is None:
        return {
            "message":"token无效"
        }

    results = load_history(
        user_id
    )

    history_list = []

    for row in results:

        history_list.append(
            {
                "destination": row[0],
                "days": row[1],
                "budget": row[2],
                "created_time": str(row[3])
            }
        )

    return {
        "user_id": user_id,
        "history": history_list
    }

@app.post("/profile")
def profile(
    user_id: int = Depends(get_current_user)
):

    print("最终user_id=", user_id)

    if user_id is None:
        return {
            "message":"token无效"
        }

    profile_data = load_profile(
        user_id
    )

    return {
        "user_id": user_id,
        "profile": profile_data
    }


from fastapi.responses import FileResponse

@app.get("/app")
def serve_frontend():
    return FileResponse("static/index.html")
