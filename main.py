import os
import sqlite3
import secrets
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from google import genai
from google.genai import types

app = FastAPI(
    title="NovAI Provider API",
    description="API indépendante pour distribuer l'accès aux modèles NovAI avec gestion de clés et de crédits dédiés."
)

# ==============================================================================
# 🗄️ BASE DE DONNÉES SQLITE POUR L'API
# ==============================================================================
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

# ==============================================================================
# ⚙️ CONFIGURATION GEMINI ET PROFILS IA
# ==============================================================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "TA_CLE_GOOGLE_GEMINI")
client = genai.Client(api_key=GEMINI_API_KEY)

PROFILS_IA = {
    "nova-3.6-flash": {
        "gemini_model": "gemini-3.6-flash",
        "temperature": 0.8,
        "system_instruction": "Tu es Nova3.6-flash, un assistant amical, cultivé et très polyvalent."
    },
    "nova-1.6-codex": {
        "gemini_model": "gemini-3.6-flash",
        "temperature": 0.2,
        "system_instruction": "Tu es Nova1.6-codex, un ingénieur logiciel senior expert en programmation."
    }
}

# ==============================================================================
# 🔒 SÉCURITÉ : VÉRIFICATION DE LA CLÉ API CLIENT
# ==============================================================================
api_key_header = APIKeyHeader(name="Authorization", auto_error=True)

def verify_api_key(api_key: str = Depends(api_key_header)):
    # Découpe le préfixe "Bearer " s'il est présent
    token = api_key.replace("Bearer ", "").strip()
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT username, api_credits FROM api_users WHERE api_key = ?", (token,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        raise HTTPException(status_code=401, detail="Clé API NovAI invalide.")
    
    username, api_credits = user
    if api_credits <= 0:
        raise HTTPException(status_code=402, detail="Crédits API épuisés. Veuillez recharger votre compte API.")
    
    return {"key": token, "username": username, "api_credits": api_credits}

# ==============================================================================
# 📋 SCHÉMAS DE REQUÊTES
# ==============================================================================
class RegisterRequest(BaseModel):
    username: str

class ChatRequest(BaseModel):
    model: str
    prompt: str

# ==============================================================================
# 🚀 ENDPOINTS DE L'API
# ==============================================================================

# 1. Inscription et Génération automatique de Clé API
@app.post("/v1/auth/register")
def register_user(req: RegisterRequest):
    new_key = f"novai_sk_{secrets.token_hex(16)}"
    credits_initiaux_api = 100  # Crédits API donnés au départ

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO api_users (api_key, username, api_credits) VALUES (?, ?, ?)",
            (new_key, req.username.strip(), credits_initiaux_api)
        )
        conn.commit()
        conn.close()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Ce nom d'utilisateur existe déjà pour l'API.")

    return {
        "status": "success",
        "message": "Clé API générée avec succès.",
        "username": req.username,
        "api_key": new_key,
        "api_credits": credits_initiaux_api
    }

# 2. Utilisation des Modèles via l'API (Consommation de Crédits API)
@app.post("/v1/chat/completions")
def chat(req: ChatRequest, user: dict = Depends(verify_api_key)):
    if req.model not in PROFILS_IA:
        raise HTTPException(
            status_code=400, 
            detail=f"Modèle inconnu. Modèles disponibles : {list(PROFILS_IA.keys())}"
        )
    
    profil = PROFILS_IA[req.model]
    
    try:
        response = client.models.generate_content(
            model=profil["gemini_model"],
            contents=req.prompt,
            config=types.GenerateContentConfig(
                system_instruction=profil["system_instruction"],
                temperature=profil["temperature"]
            )
        )
        
        # Déduction d'un crédit API
        nouveaux_credits_api = user["api_credits"] - 1
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE api_users SET api_credits = ? WHERE api_key = ?", 
            (nouveaux_credits_api, user["key"])
        )
        conn.commit()
        conn.close()
        
        return {
            "model_used": req.model,
            "response": response.text,
            "api_credits_remaining": nouveaux_credits_api
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur backend : {str(e)}")

# 3. Solde de crédits de l'API
@app.get("/v1/user/credits")
def get_credits(user: dict = Depends(verify_api_key)):
    return {
        "username": user["username"], 
        "api_credits_remaining": user["api_credits"]
    }
