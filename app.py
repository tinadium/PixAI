import os
import datetime
import streamlit as st
from google import genai
from google.genai import types

# ==============================================================================
# ⚙️ CONFIGURATION DU SCRIPT ET DES PROFILS D'IA
# ==============================================================================
API_KEY = "TA_CLE_API_ICI"  # Colle ta clé Gemini entre les guillemets
MODEL_NAME = "gemini-3.6-flash"
CREDITS_QUOTIDIENS = 140     # Nombre de crédits donnés chaque jour
IMAGE_CREDIT_PATH = "credit.png"  # Chemin vers ton image de crédit

# Mot de passe global (laisse vide "" si tu ne veux pas de mot de passe)
MOT_DE_PASSE_ACCES = ""

PROFILS_IA = {
    "💬Nova2.5-flash": {
        "description": "Conversation naturelle, polyvalente et amicale.",
        "temperature": 0.8,
        "system_instruction": """
        Tu es "Nova2.5-flash" amical, cultivé et très polyvalent.
        Tu réponds de manière fluide, naturelle et chaleureuse.
        Adaptes-toi à toutes les demandes avec clarté et concision.
        """
    },
    "💻Nova1.6-codex": {
        "description": "Optimisé pour la programmation, la revue de code et le debug.",
        "temperature": 0.2,
        "system_instruction": """
        Tu es un "Nova1.6-codex" un ingénieur logiciel senior et expert en programmation multi-langages.
        Règles :
        1. Fournis du code propre, moderne, sécurisé et parfaitement commenté.
        2. Explique brièvement la logique avant ou après les blocs de code.
        3. Identifie les pièges potentiels, bugs ou problèmes de performance.
        4. Priorise les meilleures pratiques de développement.
        """
    }
}
# ==============================================================================

# Page Configuration Streamlit
st.set_page_config(
    page_title="NovAI",
    page_icon="👾",
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

    section[data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #21262d;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# --- FORMULAIRE DE CONNEXION SIMPLIFIÉ ---
if "user_email" not in st.session_state:
    st.session_state.user_email = None

if not st.session_state.user_email:
    st.markdown('<div class="main-title">Bienvenue sur NovAI</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Entrez un identifiant pour accéder à l\'assistant et vos crédits quotidiens.</div>', unsafe_allow_html=True)
    
    with st.form("login_form"):
        email_input = st.text_input("Votre Email / Pseudo", placeholder="ex: alex@gmail.com")
        pwd_input = st.text_input("Mot de passe", type="password") if MOT_DE_PASSE_ACCES else None
        submit = st.form_submit_button("🚀 Entrer", use_container_width=True)
        
        if submit:
            if not email_input.strip():
                st.error("Veuillez saisir un identifiant.")
            elif MOT_DE_PASSE_ACCES and pwd_input != MOT_DE_PASSE_ACCES:
                st.error("Mot de passe incorrect.")
            else:
                st.session_state.user_email = email_input.strip()
                st.rerun()
    st.stop()

# --- GESTION DU RECHARGEMENT QUOTIDIEN DES CRÉDITS ---
today_str = datetime.date.today().isoformat()

if "last_login_date" not in st.session_state or st.session_state.last_login_date != today_str:
    st.session_state.last_login_date = today_str
    st.session_state.credits = CREDITS_QUOTIDIENS
    st.toast(f"🎁 Vos {CREDITS_QUOTIDIENS} crédits quotidiens ont été ajoutés !", icon="🪙")

if "credits" not in st.session_state:
    st.session_state.credits = CREDITS_QUOTIDIENS

# --- INITIALISATION CLIENT GEMINI ---
@st.cache_resource
def get_client():
    key = API_KEY if API_KEY != "TA_CLE_API_ICI" else os.environ.get("GEMINI_API_KEY")
    if not key:
        st.error("🔑 Clé API introuvable. Indique ta clé dans la variable `API_KEY` en haut du script.")
        st.stop()
    return genai.Client(api_key=key)

client = get_client()

# --- SIDEBAR (Profil, Profil IA & Déconnexion) ---
with st.sidebar:
    if os.path.exists("logo.jpg"):
        st.image("logo.jpg", width=140)
    
    st.markdown(f"**Connecté en tant que :**\n`{st.session_state.user_email}`")
    
    st.markdown("---")
    st.markdown("### 🎯 Modèle IA")
    
    profil_choisi = st.selectbox(
        "Choisis le modèle:",
        options=list(PROFILS_IA.keys()),
        index=0
    )
    st.caption(f"ℹ️ {PROFILS_IA[profil_choisi]['description']}")
    
    st.markdown("---")
    if st.button("🗑️ Réinitialiser la discussion", use_container_width=True):
        st.session_state.messages = []
        st.session_state.chat = None
        st.rerun()

    if st.button("🚪 Se déconnecter", use_container_width=True):
        st.session_state.user_email = None
        st.rerun()

# --- INITIALISATION CHAT GEMINI ---
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

# --- ENTÊTE PRINCIPAL AVEC AFFICHAGE DES CRÉDITS ET IMAGE ---
col_head, col_credit = st.columns([3, 1])

with col_head:
    st.markdown(f"""
        <div class="status-badge">
            <span class="status-dot"></span> Mode actif : {profil_choisi}
        </div>
    """, unsafe_allow_html=True)

with col_credit:
    c_num, c_img = st.columns([1, 1])
    with c_num:
        st.markdown(f"<h2 style='text-align: right; margin: 0; padding-top: 5px;'><b>{st.session_state.credits}</b></h2>", unsafe_allow_html=True)
    with c_img:
        if os.path.exists(IMAGE_CREDIT_PATH):
            st.image(IMAGE_CREDIT_PATH, width=140)
        else:
            st.markdown("<h2 style='margin: 0;'>🪙</h2>", unsafe_allow_html=True)

st.markdown('<div class="main-title">Assistant IA Personnel</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Propulsé par Google Gemini • Pose tes questions ci-dessous</div>', unsafe_allow_html=True)

# --- AFFICHAGE DU CHAT ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    avatar = "👤" if message["role"] == "user" else "🤖"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# --- ENVOI DE MESSAGE ---
if prompt := st.chat_input("Écris ton message ici..."):
    if st.session_state.credits <= 0:
        st.error("⚠️ Vous avez épuisé vos crédits ! Revenez demain ou rechargez votre compte.")
    else:
        # 1. Enregistrement et affichage immédiat du message utilisateur
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        # 2. Génération de la réponse
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner(f"L'IA ({profil_choisi}) rédige une réponse..."):
                try:
                    response = st.session_state.chat.send_message(prompt)
                    reponse_texte = response.text
                    
                    # Affichage direct de la réponse
                    st.markdown(reponse_texte)
                    
                    # Enregistrement dans l'historique
                    st.session_state.messages.append({"role": "assistant", "content": reponse_texte})
                    
                    # Décompte des crédits
                    total_caracteres = len(prompt) + len(reponse_texte)
                    credits_consommes = max(1, total_caracteres // 300)
                    st.session_state.credits = max(0, st.session_state.credits - credits_consommes)
                    
                    st.toast(f"📉 -{credits_consommes} crédit(s) utilisé(s)", icon="🪙")
                    
                except Exception as e:
                    st.error(f"Erreur de communication avec l'IA : {e}")
                    
                    # ==========================================================
                    # 🧮 CALCUL DU COÛT SELON LA LONGUEUR (PROMPT + RÉPONSE)
                    # ==========================================================
                    total_caracteres = len(prompt) + len(reponse_texte)
                    
                    # Règle : 1 crédit par tranche de 300 caractères (minimum 1)
                    credits_consommes = max(1, total_caracteres // 300)
                    
                    # Déduction des crédits
                    st.session_state.credits = max(0, st.session_state.credits - credits_consommes)
                    
                    # Notification discrète à l'utilisateur
                    st.toast(f"📉 -{credits_consommes} crédit(s) utilisé(s) ({total_caracteres} caractères)", icon="🪙")
                    
                except Exception as e:
                    st.error(f"Une erreur s'est produite : {e}")
        
        # 3. Rafraîchissement pour mettre à jour l'affichage
        st.rerun()
