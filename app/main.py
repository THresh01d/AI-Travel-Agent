from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
import requests
import os
import json


load_dotenv()

app = FastAPI()
messages = []

class ChatRequest(BaseModel):
    message: str

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

@app.get("/")
def home():
    return {"message": "AI Travel Agent Running"}

@app.post("/chat")
def chat(req: ChatRequest):

    url = "https://api.deepseek.com/chat/completions"

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    full_messages =[
        {
            "role":"system",
            "content":"""
        你是旅行信息提取助手。

        你的任务是：
        从用户输入中提取：
        1. destination
        2. days
        3. budget

        必须返回JSON格式。
        不要输出任何解释。
        """
        },
        {
        "role": "user",
        "content": req.message
    }
    ]

    data = {
        "model": "deepseek-chat",
        "messages": full_messages
    }

    response = requests.post(url, headers=headers, json=data)

    result = response.json()

    ai_reply = result["choices"][0]["message"]["content"]
    
    try:
        parsed_data = json.loads(ai_reply)

        city = parsed_data["destination"]
        days = parsed_data["days"]
        budget = parsed_data["budget"]

        city_spots = {
            "北京": ["故宫","天安门","颐和园"],
            "成都": ["宽窄巷子","熊猫基地","春熙路"],
            "上海": ["外滩","东方明珠","豫园"],
            "杭州": ["西湖","灵隐寺","河坊街"],
            "重庆": ["洪崖洞","解放碑","磁器口"],
            "西安": ["兵马俑","大雁塔","回民街"],
            "南京":["夫子庙","玄武湖","鸡鸣寺"]
        }

        spots = city_spots.get(
            city,
            ["当地热门景点"]
        )

    except Exception as e:
        return {
        "error": "AI返回的不是正确JSON",
        "raw_reply": ai_reply
    }

    plan_prompt = f"""
    请根据以下信息生成详细旅游攻略：

    城市：{city}
    天数：{days}
    预算：{budget}

    推荐景点：
    {spots}

    请按Day1 Day2格式输出。
    """

    plan_data = {
        "model": "deepseek-chat",
        "messages": [
            {
            "role":"system",
            "content":"你是专业旅游规划师"
            },
            {
            "role":"user",
            "content": plan_prompt
            }
        ]
    }

    plan_response = requests.post(
    url,
    headers=headers,
    json=plan_data
    )

    plan_result = plan_response.json()

    travel_plan = plan_result["choices"][0]["message"]["content"]

    return {
    "parsed_data": parsed_data,
    "travel_plan": travel_plan
    }
    