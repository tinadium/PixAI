import os
from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from google import genai
from google.genai import types

app = FastAPI(title="NovAI Provider API")

# --- CONFIGURATION GEMINI ---
# Mets ta vraie clé Google dans les variables d'environnement sur Render (GEMINI_API_KEY)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "TA_CLE_GOOGLE_GEMINI_ICI")
client = genai.Client(api_key=GEMINI_API_KEY)

# --- BASE DE DONNÉES EN MÉMOIRE DES CLÉS CLIENTS ---
# À remplacer plus tard par une vraie BDD (SQLite, PostgreSQL, etc.)
USERS_DB = {
    "novai-secret-key-123": {"user": "client_demo", "credits": 500},
    "novai-secret-key-999": {"user": "test_user", "credits": 50}
}

# Config des modèles NovAI
PROFILS_IA = {
    "nova-2.5-flash": {
        "gemini_model": "gemini-2.5-flash",
        "temperature": 0.8,
        "system_instruction": "Tu es Nova2.5-flash, un assistant amical et polyvalent."
    },
    "nova-1.6-codex": {
        "gemini_model": "gemini-2.5-flash", # ou autre version codex
        "temperature": 0.2,
        "system_instruction": "Tu es Nova1.6-codex, un expert en programmation."
    }
}

# --- SÉCURITÉ : VÉRIFICATION DE LA CLÉ API ---
api_key_header = APIKeyHeader(name="Authorization", auto_error=True)

def verify_api_key(api_key: str = Depends(api_key_header)):
    # Format attendu : "Bearer novai-secret-key-123"
    token = api_key.replace("Bearer ", "").strip()
    if token not in USERS_DB:
        raise HTTPException(status_code=401, detail="Clé API NovAI invalide.")
    
    user_data = USERS_DB[token]
    if user_data["credits"] <= 0:
        raise HTTPException(status_code=402, detail="Crédits insuffisants sur cette clé API.")
    
    return token

# --- STRUCTURES DES REQUÊTES / RÉPONSES ---
class ChatRequest(BaseModel):
    model: str  # "nova-2.5-flash" ou "nova-1.6-codex"
    prompt: str

class ChatResponse(BaseModel):
    model_used: str
    response: str
    credits_remaining: int

# --- ENDPOINTS ---

@app.post("/v1/chat/completions", response_model=ChatResponse)
def generate_chat(request: ChatRequest, token: str = Depends(verify_api_key)):
    if request.model not in PROFILS_IA:
        raise HTTPException(status_code=400, detail=f"Modèle inconnu. Modèles disponibles : {list(PROFILS_IA.keys())}")
    
    profil = PROFILS_IA[request.model]
    
    try:
        # Envoi à Google Gemini
        response = client.models.generate_content(
            model=profil["gemini_model"],
            contents=request.prompt,
            config=types.GenerateContentConfig(
                system_instruction=profil["system_instruction"],
                temperature=profil["temperature"]
            )
        )
        
        # Décompte des crédits (1 crédit par appel)
        USERS_DB[token]["credits"] -= 1
        
        return ChatResponse(
            model_used=request.model,
            response=response.text,
            credits_remaining=USERS_DB[token]["credits"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur interne : {str(e)}")

@app.get("/v1/user/credits")
def get_credits(token: str = Depends(verify_api_key)):
    return {
        "user": USERS_DB[token]["user"],
        "credits": USERS_DB[token]["credits"]
    }
