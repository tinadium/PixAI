import os
import sqlite3
import secrets
import streamlit as st
from google import genai
from google.genai import types

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="NovAI Studio",
    page_icon="🤖",
    layout="centered"
)

# --- CONFIGURATION DE LA BASE DE DONNÉES DES CLÉS API ---
DB_FILE = "novai_keys.db"

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

# --- CONFIGURATION DE L'API GEMINI ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "TA_CLE_GOOGLE_GEMINI")

try:
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception:
    client = None

# --- CONFIGURATION DES MODÈLES ---
PROFILS_IA = {
    "nova-3.6-flash": {
        "gemini_model": "gemini-3.6-flash",
        "temperature": 0.8,
        "description": "Assistant amical et polyvalent.",
        "system_instruction": "Tu es Nova3.6-flash, un assistant amical, cultivé et très polyvalent."
    },
    "nova-1.6-codex": {
        "gemini_model": "gemini-3.6-flash",
        "temperature": 0.2,
        "description": "Expert en code et programmation.",
        "system_instruction": "Tu es Nova1.6-codex, un ingénieur logiciel senior expert en programmation."
    }
}

# --- INITIALISATION DE LA SESSION WEB ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if "credits" not in st.session_state:
    st.session_state.credits = 140

# --- BARRE LATÉRALE (ORGANISÉE PAR ONGLETS POUR ÉVITER LE SCROLL) ---
with st.sidebar:
    st.title("⚙️ NovAI Studio")
    
    # Utilisation d'onglets dans la sidebar pour que tout soit visible directement
    tab_chat, tab_api = st.tabs(["💬 Chat", "🔑 API"])
    
    with tab_chat:
        profil_choisi = st.selectbox("Modèle", list(PROFILS_IA.keys()), label_visibility="collapsed")
        st.caption(PROFILS_IA[profil_choisi]["description"])
        
        st.markdown("---")
        st.metric("🪙 Crédits Web", f"{st.session_state.credits}/140")
        
        if st.button("Effacer le chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    with tab_api:
        st.write("**Créer une clé API**")
        pseudo_api = st.text_input("Pseudo", placeholder="ex: devalex", label_visibility="collapsed")
        
        if st.button("Générer la clé", use_container_width=True):
            if not pseudo_api.strip():
                st.error("Mets un pseudo.")
            else:
                new_key = f"novai_sk_{secrets.token_hex(16)}"
                credits_initiaux = 100
                
                try:
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO api_users (api_key, username, api_credits) VALUES (?, ?, ?)",
                        (new_key, pseudo_api.strip(), credits_initiaux)
                    )
                    conn.commit()
                    conn.close()
                    
                    st.success("Clé créée !")
                    st.code(new_key, language="text")
                except sqlite3.IntegrityError:
                    st.error("Pseudo déjà pris.")
                except Exception as e:
                    st.error(f"Erreur : {e}")

info_modele = PROFILS_IA[profil_choisi]

# --- INTERFACE PRINCIPALE DE CHAT ---
st.title("✨ NovAI Studio")
st.write(f"Mode actif : **{profil_choisi}**")

# Affichage de l'historique
for message in st.session_state.messages:
    avatar = "👤" if message["role"] == "user" else "🤖"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# --- GESTION DE L'ENVOI DE MESSAGE ---
if prompt := st.chat_input("Écris ton message ici..."):
    if st.session_state.credits <= 0:
        st.error("⚠️ Crédits web épuisés !")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Réflexion..."):
                try:
                    if not client:
                        raise Exception("Client Gemini non initialisé.")
                    
                    response = client.models.generate_content(
                        model=info_modele["gemini_model"],
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=info_modele["system_instruction"],
                            temperature=info_modele["temperature"]
                        )
                    )
                    reponse_texte = response.text
                    st.markdown(reponse_texte)
                    
                    st.session_state.messages.append({"role": "assistant", "content": reponse_texte})
                    
                    credits_consommes = max(1, (len(prompt) + len(reponse_texte)) // 300)
                    st.session_state.credits = max(0, st.session_state.credits - credits_consommes)
                    st.toast(f"📉 -{credits_consommes} crédit(s) utilisé(s)", icon="🪙")
                    
                except Exception as e:
                    st.error(f"Erreur : {e}")
