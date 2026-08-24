import datetime
import os
import streamlit as st
from google import genai
from google.genai import types

# ==============================================================================
# ⚙️ CONFIGURATION DU SCRIPT ET DES PROFILS D'IA
# ==============================================================================
# Mets ta vraie clé ici OU ajoute GEMINI_API_KEY dans les variables d'environnement sur Render
API_KEY = "TA_CLE_API_ICI"  
MODEL_NAME = "gemini-2.5-flash"
CREDITS_QUOTIDIENS = 140
IMAGE_CREDIT_PATH = "credit.png"

MOT_DE_PASSE_ACCES = ""

PROFILS_IA = {
    "💬Nova2.5-flash": {
        "description": "Conversation naturelle, polyvalente et amicale.",
        "temperature": 0.8,
        "system_instruction": "Tu es Nova, un assistant amical et polyvalent. Réponds de manière claire et fluide.",
    },
    "💻Nova1.6-codex": {
        "description": "Optimisé pour la programmation et le debug.",
        "temperature": 0.2,
        "system_instruction": "Tu es Nova-Codex, un expert en programmation. Fournis du code propre et expliqué.",
    },
}
# ==============================================================================

st.set_page_config(
    page_title="NovAI",
    page_icon="👾",
    layout="centered",
    initial_sidebar_state="expanded",
)

# 🎨 DESIGN CSS
CUSTOM_CSS = """
<style>
    .stApp { background-color: #0e1117; font-family: 'Inter', sans-serif; }
    .main-title { font-size: 2.2rem; font-weight: 800; background: linear-gradient(135deg, #a855f7 0%, #3b82f6 50%, #06b6d4 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .sub-title { color: #94a3b8; font-size: 0.95rem; margin-bottom: 1.5rem; }
    .stChatMessage { background-color: #161b22 !important; border: 1px solid #21262d !important; border-radius: 12px !important; }
    section[data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #21262d; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# --- GESTION UTILISATEUR ET CRÉDITS ---
if "user_email" not in st.session_state:
    st.session_state.user_email = None

if not st.session_state.user_email:
    st.markdown('<div class="main-title">Bienvenue sur NovAI</div>', unsafe_allow_html=True)
    with st.form("login_form"):
        email_input = st.text_input("Votre Email / Pseudo", placeholder="ex: alex@gmail.com")
        submit = st.form_submit_button("🚀 Entrer", use_container_width=True)
        if submit and email_input.strip():
            st.session_state.user_email = email_input.strip()
            st.rerun()
    st.stop()

if "credits" not in st.session_state:
    st.session_state.credits = CREDITS_QUOTIDIENS

today_str = datetime.date.today().isoformat()
if "last_login_date" not in st.session_state or st.session_state.last_login_date != today_str:
    st.session_state.last_login_date = today_str
    st.session_state.credits = CREDITS_QUOTIDIENS

# --- CLIENT GEMINI ---
@st.cache_resource
def get_client():
    key = API_KEY if API_KEY != "TA_CLE_API_ICI" else os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    return genai.Client(api_key=key)

client = get_client()

# --- SIDEBAR ---
with st.sidebar:
    if os.path.exists("logo.jpg"):
        st.image("logo.jpg", width=250)
    st.markdown(f"**Connecté :** `{st.session_state.user_email}`")
    st.markdown("---")
    profil_choisi = st.selectbox("Modèle IA:", options=list(PROFILS_IA.keys()), index=0)
    
    if st.button("🗑️ Réinitialiser", use_container_width=True):
        st.session_state.messages = []
        st.session_state.chat = None
        st.rerun()

# --- INITIALISATION CHAT ---
config_profil = PROFILS_IA[profil_choisi]

if "current_profil" not in st.session_state or st.session_state.current_profil != profil_choisi:
    st.session_state.current_profil = profil_choisi
    st.session_state.messages = []
    if client:
        st.session_state.chat = client.chats.create(
            model=MODEL_NAME,
            config=types.GenerateContentConfig(
                system_instruction=config_profil["system_instruction"],
                temperature=config_profil["temperature"],
            )
        )

# --- AFFICHAGE DE L'EN-TÊTE ---
col_head, col_credit = st.columns([3, 1])
with col_head:
    st.markdown(f'<div class="main-title">Assistant {profil_choisi}</div>', unsafe_allow_html=True)
with col_credit:
    st.markdown(f"<h2 style='text-align: right;'>🪙 <b>{st.session_state.credits}</b></h2>", unsafe_allow_html=True)

# --- HISTORIQUE DE DISCUSSION ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    avatar = "👤" if message["role"] == "user" else "🤖"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# --- ENVOI ET RÉPONSE (AVEC GESTION D'ERREUR CLAIRE) ---
if prompt := st.chat_input("Écris ton message ici..."):
    if not client:
        st.error("❌ La clé API n'est pas configurée. Ajoute ta clé Gemini dans app.py ou sur Render.")
    elif st.session_state.credits <= 0:
        st.error("⚠️ Vous n'avez plus de crédits pour aujourd'hui.")
    else:
        # 1. Message utilisateur
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        # 2. Réponse IA
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Réflexion..."):
                try:
                    response = st.session_state.chat.send_message(prompt)
                    reponse_texte = response.text

                    st.markdown(reponse_texte)
                    st.session_state.messages.append({"role": "assistant", "content": reponse_texte})

                    # Décompte simple
                    st.session_state.credits = max(0, st.session_state.credits - 1)
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Erreur lors de l'appel à l'IA : {e}")
