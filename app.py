import os
import sqlite3
import secrets
import streamlit as st
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from google import genai
import threading
import uvicorn

# --- CONFIGURATION DE LA BASE DE DONNÉES ---
DB_FILE = "novai_users.db"

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

# --- PARTIE API FASTAPI ---
api_app = FastAPI(title="NovAI Unified API")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

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

@api_app.post("/v1/chat/completions")
def api_chat(req: ChatRequest, user: dict = Depends(verify_api_key)):
    if not client:
        raise HTTPException(status_code=500, detail="Clé API Google Gemini manquante sur le serveur.")
    try:
        response = client.models.generate_content(
            model=req.model,
            contents=req.prompt
        )
        
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

# --- LANCEMENT DE L'API EN ARRIÉR PLAN POUR STREAMLIT ---
def run_fastapi():
    uvicorn.run(api_app, host="0.0.0.0", port=8001, log_level="warning")

@st.cache_resource
def start_background_api():
    t = threading.Thread(target=run_fastapi, daemon=True)
    t.start()

start_background_api()

# --- PARTIE INTERFACE STREAMLIT ---
st.set_page_config(page_title="NovAI Studio", page_icon="💬")

st.sidebar.title("Menu NovAI")
menu = st.sidebar.radio("Navigation", ["💬 Chat", "🔑 API"])

if menu == "💬 Chat":
    st.title("💬 Chat avec NovAI")
    st.write("Bienvenue sur ton application unifiée !")
    
    prompt = st.text_input("Écris ton message :")
    if st.button("Envoyer") and prompt:
        if client:
            try:
                res = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
                st.write(res.text)
            except Exception as e:
                st.error(f"Erreur : {e}")
        else:
            st.error("La variable GEMINI_API_KEY n'est pas configurée sur Render.")

elif menu == "🔑 API":
    st.title("🔑 Gestion de votre clé API")
    st.write("Générez votre clé pour l'utiliser dans vos scripts externes sur le point de terminaison `/v1/chat/completions`.")
    
    username = st.text_input("Entrez votre pseudo :")
    if st.button("Générer ma clé API"):
        if username.strip():
            api_key = f"novai_sk_{secrets.token_hex(16)}"
            initial_credits = 100
            try:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO api_users (api_key, username, api_credits) VALUES (?, ?, ?)",
                    (api_key, username, initial_credits)
                )
                conn.commit()
                conn.close()
                st.success("Clé générée avec succès !")
                st.code(api_key, language="text")
                st.info(f"Crédits initiaux : {initial_credits}")
            except sqlite3.IntegrityError:
                st.error("Ce pseudo est déjà utilisé. Choisissez-en un autre.")
        else:
            st.warning("Veuillez entrer un pseudo valide.")
