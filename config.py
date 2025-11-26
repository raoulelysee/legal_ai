"""
Configuration centralisée de l'application.
Toutes les constantes et variables d'environnement sont chargées ici.
"""

import os
from dotenv import load_dotenv

# Charge les variables d'environnement
load_dotenv()


class Config:
    """Configuration de l'application."""

    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

    # Pinecone Configuration
    PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
    PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
    PINECONE_NAMESPACE = os.getenv("PINECONE_NAMESPACE")

    # Modèles
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    EXPANDER_MODEL = os.getenv("EXPANDER_MODEL", "llama-3.3-70b-versatile")
    SYNTHESIZER_MODEL = os.getenv("SYNTHESIZER_MODEL", "llama-3.3-70b-versatile")

    # Paramètres RAG
    MIN_SIMILARITY_SCORE = float(os.getenv("MIN_SIMILARITY_SCORE", "0.55"))
    MAX_CONTEXT_TOKENS = int(os.getenv("MAX_CONTEXT_TOKENS", "12000"))
    MIN_CONTEXT_LENGTH = int(os.getenv("MIN_CONTEXT_LENGTH", "100"))

    # URLs
    GROQ_BASE_URL = "https://api.groq.com/openai/v1"

    # Protection de l'application
    ENABLE_PASSWORD_PROTECTION = os.getenv("ENABLE_PASSWORD_PROTECTION", "false").lower() == "true"
    APP_PASSWORD = os.getenv("APP_PASSWORD", "")

    # LangSmith (optionnel - pour le traçage et debugging)
    LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY", "")
    LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "encyclopedie-juridique")

    # Textes légaux
    LEGAL_DISCLAIMER = (
        "Ceci n'est pas un conseil juridique professionnel. "
        "Consultez toujours un avocat ou un notaire pour obtenir "
        "des conseils adaptés à votre situation."
    )

    @classmethod
    def setup_langsmith(cls):
        """Configure LangSmith si activé."""
        if cls.LANGCHAIN_TRACING_V2 and cls.LANGCHAIN_API_KEY:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = cls.LANGCHAIN_API_KEY
            os.environ["LANGCHAIN_PROJECT"] = cls.LANGCHAIN_PROJECT
            return True
        return False

    @classmethod
    def validate(cls):
        """Valide que toutes les clés API requises sont présentes."""
        required_keys = {
            "OPENAI_API_KEY": cls.OPENAI_API_KEY,
            "PINECONE_API_KEY": cls.PINECONE_API_KEY,
            "GROQ_API_KEY": cls.GROQ_API_KEY,
            "TAVILY_API_KEY": cls.TAVILY_API_KEY,
            "PINECONE_INDEX_NAME": cls.PINECONE_INDEX_NAME,
        }

        missing = [key for key, value in required_keys.items() if not value]

        if missing:
            raise ValueError(
                f"Clés API manquantes: {', '.join(missing)}. "
                f"Veuillez les configurer dans le fichier .env"
            )

        return True
