import os
import sqlite3
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from google import genai
from google.genai import types

app = FastAPI(title="NovAI API")

DB_FILE = "novai_api_users.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_users (
            api_key TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            api_credits INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "TA_CLE_GOOGLE_GEMINI")
client = genai.Client(api_key=GEMINI_API_KEY)

api_key_header = APIKeyHeader(name="Authorization", auto_error=True)

def verify_api_key(api_key: str = Depends(api_key_header)):
    token = api_key.replace("Bearer ", "").strip()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT username, api_credits FROM api_users WHERE api_key = ?", (token,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        raise HTTPException(status_code=401, detail="Clé API invalide.")
    
    username, api_credits = user
    if api_credits <= 0:
        raise HTTPException(status_code=402, detail="Crédits API épuisés.")
    
    return {"key": token, "username": username, "api_credits": api_credits}

class ChatRequest(BaseModel):
    model: str = "gemini-2.5-flash"
    prompt: str

@app.post("/v1/chat/completions")
def chat(req: ChatRequest, user: dict = Depends(verify_api_key)):
    try:
        response = client.models.generate_content(
            model=req.model,
            contents=req.prompt
        )
        
        # Décompte des crédits API
        nouveaux_credits = user["api_credits"] - 1
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE api_users SET api_credits = ? WHERE api_key = ?", (nouveaux_credits, user["key"]))
        conn.commit()
        conn.close()
        
        return {
            "response": response.text,
            "api_credits_remaining": nouveaux_credits
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
