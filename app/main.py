from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class ChatRequest(BaseModel):
    message: str

@app.get("/")
def home():
    return {"message": "AI Travel Agent Running"}

@app.post("/chat")
def chat(req: ChatRequest):
    return {
        "user_message": req.message,
        "ai_response": f"你刚刚说了: {req.message}"
    }    