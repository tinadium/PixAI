import os
import streamlit as st
from google import genai
from google.genai import types

# ==============================================================================
# ⚙️ CONFIGURATION DU SCRIPT ET DES PROFILS D'IA
# ==============================================================================
API_KEY = "TA_CLE_API_ICI"  # Colle ta clé Gemini entre les guillemets
MODEL_NAME = "gemini-3.6-flash"

# Dictionnaire des profils d'IA avec leurs consignes et paramètres dédiés :
PROFILS_IA = {
    "💬 Assistant Discussion": {
        "description": "Conversation naturelle, polyvalente et amicale.",
        "temperature": 0.7,
        "system_instruction": """
        Tu es un assistant virtuel amical, cultivé et très polyvalent.
        Tu réponds de manière fluide, naturelle et chaleureuse.
        Adaptes-toi à toutes les demandes avec clarté et concision.
        """
    },
    "💻 Expert Code & Dev": {
        "description": "Optimisé pour la programmation, la revue de code et le debug.",
        "temperature": 0.2, # Température basse pour plus de précision technique
        "system_instruction": """
        Tu es un ingénieur logiciel senior et expert en programmation multi-langages.
        Règles :
        1. Fournis du code propre, moderne, sécurisé et parfaitement commenté.
        2. Explique brièvement la logique avant ou après les blocs de code.
        3. Identifie les pièges potentiels, bugs ou problèmes de performance.
        4. Priorise les meilleures pratiques de développement.
        """
    },
    "✍️ Rédacteur & Correcteur": {
        "description": "Rédaction d'articles, relecture, style et synthèse.",
        "temperature": 0.8,
        "system_instruction": """
        Tu es un rédacteur professionnel et expert en communication écrite.
        Règles :
        1. Adopte un style irréprochable, élégant et sans faute d'orthographe.
        2. Aide à structurer les idées (titres, paragraphes, accroches).
        3. Propose des reformulations ou des corrections de textes si demandé.
        """
    },
    "🧠 Professeur & Pédagogue": {
        "description": "Explications simples de concepts complexes avec des exemples.",
        "temperature": 0.5,
        "system_instruction": """
        Tu es un professeur bienveillant et très pédagogue.
        Règles :
        1. Explique les concepts étape par étape, en utilisant des analogies simples.
        2. Évite le jargon inutile ou explique-le clairement.
        3. Termine souvent par un petit exemple concret ou une question de vérification.
        """
    }
}
# ==============================================================================

# Page Configuration Streamlit
st.set_page_config(
    page_title="Assistant IA - Multiprofils",
    page_icon="✨",
    layout="centered",
    initial_sidebar_state="expanded"
)

# 🎨 DESIGN CSS SUR MESURE
CUSTOM_CSS = """
<style>
    .stApp {
        background-color: #0e1117;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #a855f7 0%, #3b82f6 50%, #06b6d4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }

    .sub-title {
        color: #94a3b8;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }

    .status-badge {
        display: inline-flex;
        align-items: center;
        background: rgba(168, 85, 247, 0.1);
        border: 1px solid rgba(168, 85, 247, 0.3);
        padding: 4px 12px;
        border-radius: 20px;
        color: #c084fc;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }

    .status-dot {
        width: 8px;
        height: 8px;
        background-color: #10b981;
        border-radius: 50%;
        margin-right: 8px;
        box-shadow: 0 0 8px #10b981;
    }

    .stChatMessage {
        background-color: #161b22 !important;
        border: 1px solid #21262d !important;
        border-radius: 12px !important;
        padding: 14px 18px !important;
        margin-bottom: 12px !important;
        transition: all 0.2s ease-in-out;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }

    .stChatMessage:hover {
        border-color: #30363d !important;
        box-shadow: 0 6px 12px -2px rgba(0, 0, 0, 0.25);
    }

    [data-testid="stChatMessage"]:nth-child(even) {
        background-color: #1c2128 !important;
        border-left: 3px solid #a855f7 !important;
    }

    [data-testid="stChatMessage"]:nth-child(odd) {
        border-left: 3px solid #3b82f6 !important;
    }

    .stChatInputContainer {
        border-radius: 12px !important;
        border: 1px solid #30363d !important;
        background-color: #161b22 !important;
    }

    .stChatInputContainer:focus-within {
        border-color: #a855f7 !important;
        box-shadow: 0 0 0 1px #a855f7 !important;
    }

    section[data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #21262d;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Initialisation du client Google GenAI
@st.cache_resource
def get_client():
    key = API_KEY if API_KEY != "TA_CLE_API_ICI" else os.environ.get("GEMINI_API_KEY")
    if not key:
        st.error("🔑 Clé API introuvable. Indique ta clé dans la variable `API_KEY` en haut du script.")
        st.stop()
    return genai.Client(api_key=key)

client = get_client()

# --- SIDEBAR (Choix du Profil & Actions) ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/8/8a/Google_Gemini_logo.svg", width=140)
    st.markdown("### 🎯 Mode de l'IA")
    
    # Sélecteur de profil
    profil_choisi = st.selectbox(
        "Choisis le rôle de l'IA :",
        options=list(PROFILS_IA.keys()),
        index=0
    )
    
    # Infos sur le profil sélectionné
    st.caption(f"ℹ️ {PROFILS_IA[profil_choisi]['description']}")
    
    st.markdown("---")
    if st.button("🗑️ Réinitialiser la discussion", use_container_width=True):
        st.session_state.messages = []
        st.session_state.chat = None
        st.rerun()

# Initialisation ou réinitialisation du Chat selon le profil
config_profil = PROFILS_IA[profil_choisi]

if "current_profil" not in st.session_state or st.session_state.current_profil != profil_choisi:
    st.session_state.current_profil = profil_choisi
    st.session_state.messages = []
    st.session_state.chat = client.chats.create(
        model=MODEL_NAME,
        config=types.GenerateContentConfig(
            system_instruction=config_profil["system_instruction"],
            temperature=config_profil["temperature"],
        )
    )

# --- ENTÊTE PRINCIPAL ---
st.markdown(f"""
    <div class="status-badge">
        <span class="status-dot"></span> Mode actif : {profil_choisi}
    </div>
    <div class="main-title">Assistant IA Personnel</div>
    <div class="sub-title">Propulsé par Google Gemini • Pose tes questions ci-dessous</div>
""", unsafe_allow_html=True)

# --- AFFICHAGE DU CHAT ---
for message in st.session_state.messages:
    avatar = "👤" if message["role"] == "user" else "🤖"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# --- ENVOI DE MESSAGE ---
if prompt := st.chat_input("Écris ton message ici..."):
    # Message Utilisateur
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    # Réponse de l'IA
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner(f"L'IA ({profil_choisi}) rédige une réponse..."):
            try:
                response = st.session_state.chat.send_message(prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"Une erreur s'est produite : {e}")
