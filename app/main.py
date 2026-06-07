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

import os

current_user_id = None

load_dotenv()

app = FastAPI()

class ChatRequest(BaseModel):
    message: str

class RegisterRequest(BaseModel):
    username: str
    password: str

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

    global current_user_id

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

    current_user_id = user[0]

    return {
        "message": "登录成功",
        "user_id": current_user_id
    }

@app.post("/chat")
def chat(req: ChatRequest):
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

        if current_user_id is None:
            return {
                "message": "请先登录"
            }

        if profile:
            save_profile(
                user_id=current_user_id,
                profile=profile
            )

        saved_profile = load_profile(
            user_id=current_user_id
        )

        city = parsed_data.get("destination")
        days = parsed_data.get("days")
        budget = parsed_data.get("budget")
        if city:
            save_history(
                current_user_id,
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
def agent(req: ChatRequest):

    global current_user_id

    if current_user_id is None:
        return {
            "message":"请先登录"
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
            current_user_id
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
            current_user_id
        )

        history = get_user_history(
            current_user_id
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
            current_user_id
        )

        history = get_user_history(
            current_user_id
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
            current_user_id
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
            current_user_id
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
            current_user_id,
            city,
            days,
            budget
        )

        return {
            "tool":"travel",
            "travel_plan":travel_plan
        }
    

@app.get("/history")
def history():

    global current_user_id

    if current_user_id is None:

        return {
            "message": "请先登录"
        }

    results = load_history(
        current_user_id
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
        "user_id": current_user_id,
        "history": history_list
    }

@app.get("/profile")
def profile():

    global current_user_id

    if current_user_id is None:
        return {
            "message": "请先登录"
        }

    profile_data = load_profile(
        current_user_id
    )

    return {
        "user_id": current_user_id,
        "profile": profile_data
    }