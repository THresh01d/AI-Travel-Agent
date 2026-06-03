from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv

from app.database import save_profile
from app.database import load_profile
from app.knowledge_base import city_spots

from app.services.ai_service import extract_travel_info
from app.services.ai_service import generate_plan

import os


load_dotenv()

app = FastAPI()

class ChatRequest(BaseModel):
    message: str

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")


@app.get("/")
def home():
    return {"message": "AI Travel Agent Running"}

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

        if profile:
            save_profile(
            user_id=1,
            profile=profile
        )

        saved_profile = load_profile(user_id=1)

        city = parsed_data.get("destination")
        days = parsed_data.get("days")
        budget = parsed_data.get("budget")

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