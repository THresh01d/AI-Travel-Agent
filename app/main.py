from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv

from app.database import save_profile
from app.database import load_profile
from app.database import create_user
from app.database import get_user_by_username
from app.database import save_history
from app.database import load_history
from app.knowledge_base import city_spots

from app.services.ai_service import extract_travel_info
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

import os

load_dotenv()

app = FastAPI()

class ChatRequest(BaseModel):
    message: str
    token: str

class RegisterRequest(BaseModel):
    username: str
    password: str

class TokenRequest(BaseModel):
    token: str

class AgentRequest(BaseModel):
    message: str
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
        req.password
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

    if user[2] != req.password:
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

@app.post("/me")
def me(req: TokenRequest):

    user_id = verify_token(
        req.token
    )

    if not user_id:
        return {
            "message": "token无效"
        }

    return {
        "user_id": user_id
    }

@app.post("/chat")
def chat(req: ChatRequest):

    user_id = verify_token(
        req.token
    )

    if not user_id:
        return {
            "message": "token无效"
        }

    try:

        parsed_data = extract_travel_info(
            DEEPSEEK_API_KEY,
            req.message
        )

        profile = parsed_data.get(
            "profile",
            {}
        )

        print(profile)
        print(type(profile))

        if profile:
            save_profile(
                user_id=user_id,
                profile=profile
            )

        saved_profile = load_profile(
            user_id=user_id
        )

        city = parsed_data.get("destination")
        days = parsed_data.get("days")
        budget = parsed_data.get("budget")

        if city:
            save_history(
                user_id,
                city,
                days,
                budget
            )

        spots = city_spots.get(
            city,
            ["当地热门景点"]
        )

    except Exception as e:
        return {
            "error": str(e)
        }

    if city is None or days is None:
        return {
        "message":"用户偏好已保存",
        "parsed_data": parsed_data
    }

    else:
        travel_plan = generate_plan(
        DEEPSEEK_API_KEY,
        city,
        days,
        budget,
        saved_profile,
        spots
    )
        return {
        "parsed_data": parsed_data,
        "saved_profile": saved_profile,
        "travel_plan": travel_plan
    }

@app.post("/agent")
def agent(req: AgentRequest):
    
    user_id = verify_token(
        req.token
    )

    if not user_id:
        return {
            "message":"token无效"
        }

    question = req.message

    tool_result = choose_tool(
        DEEPSEEK_API_KEY,
        question
    )

    tool = tool_result["tool"]

    print(tool)

    if tool == "history":

        history = get_user_history(
            user_id
        )

        answer = summarize_history(
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

        answer = recommend_city(
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

        answer = analyze_user(
            DEEPSEEK_API_KEY,
            profile,
            history
        )

        return {
            "answer": answer
        }

    if tool == "profile":

        profile = get_user_profile(
            user_id
        )

        answer = summarize_profile(
            DEEPSEEK_API_KEY,
            profile
        )

        return {
            "answer": answer
        }

    elif tool == "travel":

        parsed_data = extract_travel_info(
            DEEPSEEK_API_KEY,
            req.message
        )

        city = parsed_data.get("destination")
        days = parsed_data.get("days")
        budget = parsed_data.get("budget")

        saved_profile = load_profile(
            user_id
        )

        spots = city_spots.get(
            city,
            ["当地热门景点"]
        )

        travel_plan = generate_plan(
            DEEPSEEK_API_KEY,
            city,
            days,
            budget,
            saved_profile,
            spots
        )

        save_history(
            user_id,
            city,
            days,
            budget
        )

        return {
            "tool":"travel",
            "travel_plan":travel_plan
        }
    

@app.post("/history")
def history(req: TokenRequest):

    user_id = verify_token(
        req.token
    )

    if not user_id:
        return {
            "message": "token无效"
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
def profile(req: TokenRequest):

    user_id = verify_token(
        req.token
    )

    if not user_id:
        return {
            "message": "token无效"
        }

    profile_data = load_profile(
        user_id
    )

    return {
        "user_id": user_id,
        "profile": profile_data
    }