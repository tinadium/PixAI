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
        "description": "Assistant amical, rapide et polyvalent pour tous les jours.",
        "system_instruction": "Tu es Nova3.6-flash, un assistant amical, cultivé et très polyvalent."
    },
    "nova-1.6-codex": {
        "gemini_model": "gemini-3.6-flash",
        "temperature": 0.2,
        "description": "Ingénieur logiciel senior expert en code et programmation.",
        "system_instruction": "Tu es Nova1.6-codex, un ingénieur logiciel senior expert en programmation."
    }
}

# --- INITIALISATION DE LA SESSION WEB ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if "credits" not in st.session_state:
    st.session_state.credits = 140  # Crédits pour l'interface web

# --- BARRE LATÉRALE (SIDEBAR) ---
with st.sidebar:
    st.title("⚙️ Paramètres NovAI")
    
    # Choix du modèle pour le chat web
    profil_choisi = st.selectbox("Choisir le modèle", list(PROFILS_IA.keys()))
    info_modele = PROFILS_IA[profil_choisi]
    st.caption(info_modele["description"])
    
    st.markdown("---")
    st.metric("🪙 Vos crédits Web", f"{st.session_state.credits} / 140")
    
    if st.button("Réinitialiser la conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    # --- SECTION : CRÉATION DE CLÉ API DIRECTE ---
    st.markdown("---")
    st.markdown("### 🔑 Espace Développeur API")
    st.write("Génère ta propre clé API NovAI directement ici.")
    
    with st.expander("Créer une clé API"):
        pseudo_api = st.text_input("Nom d'utilisateur", placeholder="ex: devalex", key="input_pseudo_api")
        if st.button("Générer ma clé API", use_container_width=True):
            if not pseudo_api.strip():
                st.error("Entre un nom d'utilisateur valide.")
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
                    
                    st.success("Clé créée avec succès !")
                    st.code(new_key, language="text")
                    st.info(f"🎁 {credits_initiaux} crédits API associés !")
                except sqlite3.IntegrityError:
                    st.error("Ce nom d'utilisateur est déjà pris. Choisis-en un autre.")
                except Exception as e:
                    st.error(f"Erreur lors de la création : {e}")

# --- INTERFACE PRINCIPALE DE CHAT ---
st.title("✨ NovAI Studio")
st.write(f"Mode actif : **{profil_choisi}**")

# Affichage de l'historique des messages
for message in st.session_state.messages:
    avatar = "👤" if message["role"] == "user" else "🤖"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# --- GESTION DE L'ENVOI DE MESSAGE ---
if prompt := st.chat_input("Écris ton message ici..."):
    if st.session_state.credits <= 0:
        st.error("⚠️ Vous avez épuisé vos crédits web ! Rechargez ou revenez plus tard.")
    else:
        # Enregistrement et affichage du message utilisateur
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        # Génération de la réponse via Gemini
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner(f"L'IA ({profil_choisi}) réfléchit..."):
                try:
                    if not client:
                        raise Exception("Client Gemini non initialisé. Vérifiez votre clé API Google.")
                    
                    response = client.models.generate_content(
                        model=info_modele["gemini_model"],
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=info_modele["system_instruction"],
                            temperature=info_modele["temperature"]
                        )
                    )
                    reponse_texte = response.text
                    
                    # Affichage direct de la réponse
                    st.markdown(reponse_texte)
                    
                    # Enregistrement dans l'historique
                    st.session_state.messages.append({"role": "assistant", "content": reponse_texte})
                    
                    # Décompte des crédits web
                    total_caracteres = len(prompt) + len(reponse_texte)
                    credits_consommes = max(1, total_caracteres // 300)
                    st.session_state.credits = max(0, st.session_state.credits - credits_consommes)
                    
                    st.toast(f"📉 -{credits_consommes} crédit(s) web utilisé(s)", icon="🪙")
                    
                except Exception as e:
                    st.error(f"Erreur de communication avec l'IA : {e}")
