from fastapi import FastAPI
from fastapi import Depends
from pydantic import BaseModel
from dotenv import load_dotenv

from app.database import save_profile
from app.database import load_profile
from app.database import create_user
from app.database import get_user_by_username
from app.database import save_history
from app.database import load_history

from app.knowledge.vector_store import init_knowledge_base, search_spots

from app.services.ai_service import generate_plan
from app.services.agent_service import get_user_profile
from app.services.agent_service import get_user_history
from app.services.tool_router import choose_tool
from app.services.summary_service import summarize_profile
from app.services.summary_service import summarize_history
from app.services.recommend_service import recommend_city
from app.services.analysis_service import analyze_user
from app.services.auth_service import create_token
from app.services.auth_service import verify_token
from app.services.dependency import get_current_user
from app.services.auth_service import hash_password
from app.services.auth_service import verify_password 

import os

load_dotenv()

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    init_knowledge_base()
    yield
    # 关闭时执行（你暂时不需要做什么，留空）

app = FastAPI(lifespan=lifespan)


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

    print("agent user_id=", user_id)

    if user_id is None:
        return {
            "message":"token无效"
        }

    question = req.message

    tool, args = await choose_tool(
        DEEPSEEK_API_KEY,
        question
    )

    print(tool)

    if tool == "history":

        history = get_user_history(
            user_id
        )

        answer = await summarize_history(
            DEEPSEEK_API_KEY,
            history
        )

        return {
            "answer": answer
        }

    if tool == "recommend":

        profile = load_profile(
            user_id
        )

        history = get_user_history(
            user_id
        )

        answer = await recommend_city(
            DEEPSEEK_API_KEY,
            profile,
            history
        )

        return {
            "answer": answer
        }
    
    if tool == "analysis":

        profile = load_profile(
            user_id
        )

        history = get_user_history(
            user_id
        )

        answer = await analyze_user(
            DEEPSEEK_API_KEY,
            profile,
            history
        )

        return {
            "answer": answer
        }

    if tool == "profile":
        new_profile = {k: v for k, v in args.items() if v}
        
        if new_profile:
            save_profile(
                user_id=user_id, 
                profile=new_profile
            )
        
        profile = get_user_profile(user_id)
        answer = await summarize_profile(DEEPSEEK_API_KEY, profile)
        return {
            "answer": 
            answer
        }


    elif tool == "travel":
        ai_city = args.get("destination")
        days = args.get("days")
        budget = args.get("budget")
        
        preference = args.get("preference")
        if preference:
            save_profile(
                user_id=user_id, 
                profile={"preference": preference}
            )
        
        saved_profile = load_profile(user_id)
        spots, rag_city = search_spots(req.message, top_k=3)
        
        city = ai_city or rag_city
        days = days or 3
        
        if ai_city and days:
            save_history(user_id, city, days, budget)
        
        travel_plan = await generate_plan(
            DEEPSEEK_API_KEY, 
            city, 
            days, 
            budget, 
            saved_profile, 
            spots
        )

        return {
            "tool": "travel", 
            "travel_plan": travel_plan
        }

    

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
