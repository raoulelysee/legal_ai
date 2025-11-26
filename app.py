import sys
import logging
import streamlit as st
from streamlit_mic_recorder import mic_recorder

from config import Config
from rag_engine import ImprovedFusionRAGQuery
from audio_utils import AudioManager

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Configuration de LangSmith (optionnel)
if Config.setup_langsmith():
    logger.info("✅ LangSmith traçage activé")
else:
    logger.info("ℹ️  LangSmith traçage désactivé")


# --- Configuration Streamlit ---
st.set_page_config(
    page_title="Répertoire de lois du Qc et du Canada(en apprentissage)",
    page_icon="⚖️",
    layout="wide"
)


def check_password():
    if not Config.ENABLE_PASSWORD_PROTECTION:
        return True

    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    # Affiche le formulaire de mot de passe
    st.title("🔐 Accès protégé")
    st.markdown("Cette application nécessite un mot de passe.")

    password = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        if password == Config.APP_PASSWORD:
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.error("❌ Mot de passe incorrect")

    st.stop()
    return False


@st.cache_resource
def get_rag_engine():
    """Initialise le moteur RAG (une seule fois)."""
    logger.info("🚀 Initialisation du moteur RAG...")
    return ImprovedFusionRAGQuery()


@st.cache_resource
def get_audio_manager():
    """Initialise le gestionnaire audio (une seule fois)."""
    try:
        return AudioManager()
    except Exception as e:
        logger.error(f"❌ Erreur initialisation audio: {e}")
        return None


def render_css():
    """Applique les styles CSS personnalisés."""
    st.markdown("""
    <style>
        /* Réserve de l'espace en bas pour la barre fixe */
        .main .block-container {
            padding-bottom: 140px;
        }

        /* Barre d'input fixe en bas */
        .input-bar-container {
            position: fixed;
            bottom: 0;
            left: 0;
            width: 100%;
            padding: 20px 40px 30px;
            background-color: #ffffff;
            border-top: 1px solid #e0e0e0;
            z-index: 99;
        }

        /* Mode sombre */
        [data-theme="dark"] .input-bar-container {
            background-color: #0e1117;
            border-top: 1px solid #262730;
        }

        /* Alignement du formulaire */
        div[data-testid="stForm"] {
            border: none;
            padding: 0;
            box-shadow: none;
        }

        div[data-testid="stForm"] > div[data-testid="stHorizontalBlock"] {
            gap: 0.5rem;
        }

        /* Badge de source */
        .source-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: 600;
            margin-left: 8px;
        }

        .source-pinecone {
            background-color: #d4edda;
            color: #155724;
        }

        .source-web {
            background-color: #fff3cd;
            color: #856404;
        }

        [data-theme="dark"] .source-pinecone {
            background-color: #155724;
            color: #d4edda;
        }

        [data-theme="dark"] .source-web {
            background-color: #856404;
            color: #fff3cd;
        }
    </style>
    """, unsafe_allow_html=True)


def render_sidebar():
    with st.sidebar:
        st.header("⚙️ Options")

        if st.button("🗑️ Effacer l'historique", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

        st.markdown("---")
        st.markdown("### 📊 Statistiques")
        st.metric("Messages", len(st.session_state.messages))

        st.markdown("---")
        st.markdown("### 🔧 Caractéristiques")
        st.markdown("""
        ✅ Recherche élargie (20 résultats)
        ✅ Filtrage par similarité (≥55%)
        ✅ Expansion de requêtes intelligente
        ✅ Extraction d'entités juridiques
        ✅ Citations des sources avec scores
        ✅ Support audio (STT & TTS)
        """)

        st.markdown("---")
        st.markdown("### ℹ️ À propos")
        st.markdown("""
        Cette application utilise l'IA pour répondre
        à vos questions juridiques sur le droit québécois.

        **Note:** Les réponses sont informatives uniquement
        et ne constituent pas des conseils juridiques.
        """)


def render_message_badges(metadata: dict):
    badges = []

    if metadata.get("used_pinecone"):
        chunks = metadata.get("chunks_found", 0)
        badges.append(
            f'<span class="source-badge source-pinecone">📚 Base de données ({chunks} chunks)</span>'
        )

    if metadata.get("used_web"):
        badges.append(
            '<span class="source-badge source-web">🌐 Web</span>'
        )

    if badges:
        st.markdown(" ".join(badges), unsafe_allow_html=True)


def render_chat_history():
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            if message["role"] == "assistant" and "metadata" in message:
                render_message_badges(message["metadata"])


def render_input_bar(audio_manager):
    with st.container():
        st.markdown('<div class="input-bar-container">', unsafe_allow_html=True)
        col1, col2 = st.columns([5, 1])

        text_prompt = None
        audio_data = None

        with col1:
            with st.form(key="input_form", clear_on_submit=True):
                col_text, col_submit = st.columns([4, 1])
                with col_text:
                    text_prompt = st.text_input(
                        "Posez votre question juridique...",
                        label_visibility="collapsed",
                        placeholder="Ex: Quelles sont les conditions de validité d'un contrat au Québec?"
                    )
                with col_submit:
                    submit_button = st.form_submit_button("Envoyer")

        with col2:
            if audio_manager:
                audio_data = mic_recorder(
                    start_prompt="🎤",
                    stop_prompt="⏹️",
                    key='recorder',
                    use_container_width=True
                )

        st.markdown('</div>', unsafe_allow_html=True)

        return text_prompt if submit_button and text_prompt else None, audio_data


def process_query(prompt: str, rag_engine, audio_manager, is_audio_input: bool):
    # Génère un user_id pour le rate limiting (basé sur la session Streamlit)
    import hashlib
    if "user_id" not in st.session_state:
        # Crée un ID unique par session
        session_id = str(id(st.session_state))
        st.session_state.user_id = hashlib.md5(session_id.encode()).hexdigest()[:16]

    user_id = st.session_state.user_id

    # Ajoute le message utilisateur
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    # Génère la réponse
    with st.chat_message("assistant"):
        with st.spinner("🔍 Recherche approfondie en cours..."):
            try:
                # Passe le user_id pour le rate limiting
                response_text, metadata = rag_engine.query(prompt, user_id=user_id)
                st.markdown(response_text)
                render_message_badges(metadata)

            except Exception as e:
                logger.error(f"❌ Erreur génération réponse: {e}", exc_info=True)
                response_text = f"Désolé, une erreur s'est produite. Veuillez réessayer.\n\n{Config.LEGAL_DISCLAIMER}"
                metadata = {"error": True}
                st.error("Une erreur s'est produite lors de la génération de la réponse.")

        # Audio (seulement si entrée audio et clients disponibles)
        if is_audio_input and audio_manager:
            with st.spinner("🔊 Génération de l'audio..."):
                audio_response = audio_manager.generate_audio(response_text)
                if audio_response:
                    st.audio(audio_response, autoplay=True)

    # Sauvegarde le message
    st.session_state.messages.append({
        "role": "assistant",
        "content": response_text,
        "metadata": metadata
    })

    # Rerun seulement pour les entrées texte
    if not is_audio_input:
        st.rerun()


def main():
    # Vérification du mot de passe si nécessaire
    check_password()

    # Titre et disclaimer
    st.title("⚖️ Répertoire juridique Qc & Canada (en apprentissage)")
    st.caption(
        "Le contenu de ce site est purement informatif et ne peut être interprété comme un avis juridique. "
        "L'utilisateur ne devrait prendre aucune décision en se basant uniquement sur ces renseignements. "
        "Consultez toujours un professionnel du droit pour des conseils adaptés à votre situation."
    )
    st.markdown("")

    # Applique les styles
    render_css()

    # Valide la configuration
    try:
        Config.validate()
    except ValueError as e:
        st.error(f"❌ Configuration invalide: {e}")
        st.info("Ajoutez les clés API manquantes dans votre fichier .env")
        st.stop()

    # Initialisation des composants
    try:
        rag_engine = get_rag_engine()
        audio_manager = get_audio_manager()
    except Exception as e:
        logger.error(f"❌ Erreur initialisation: {e}")
        st.error(f"Erreur d'initialisation: {e}")
        st.stop()

    # Initialisation de l'état de session
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "last_input_method" not in st.session_state:
        st.session_state.last_input_method = "text"
    if "processed_audio_id" not in st.session_state:
        st.session_state.processed_audio_id = None

    # Affiche la sidebar
    render_sidebar()

    # Affiche l'historique
    render_chat_history()

    # Barre d'input
    text_prompt, audio_data = render_input_bar(audio_manager)

    # Traitement de l'entrée
    prompt = None
    is_audio_input = False

    if text_prompt:
        prompt = text_prompt
        st.session_state.last_input_method = "text"

    elif audio_data and audio_data['id'] != st.session_state.processed_audio_id:
        st.session_state.last_input_method = "audio"
        is_audio_input = True

        with st.spinner("Transcription de l'audio..."):
            if audio_manager:
                prompt = audio_manager.transcribe_audio(audio_data['bytes'])

        st.session_state.processed_audio_id = audio_data['id']

    # Génération de la réponse
    if prompt:
        process_query(prompt, rag_engine, audio_manager, is_audio_input)


if __name__ == "__main__":
    main()
