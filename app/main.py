from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
import requests
import os

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

    messages.append({
        "role": "user",
        "content": req.message
    })

    full_messages =[
        {
            "role":"system",
            "content":"你是一个专业的旅游规划师,擅长生成旅行攻略"
        }
    ] +messages

    data = {
        "model": "deepseek-chat",
        "messages": full_messages
    }

    response = requests.post(url, headers=headers, json=data)

    result = response.json()

    ai_reply = result["choices"][0]["message"]["content"]

    messages.append({
        "role": "assistant",
        "content": ai_reply
    })

    return {
        "user_message": req.message,
        "ai_response": ai_reply
    }

    