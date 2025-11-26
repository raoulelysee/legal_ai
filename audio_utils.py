"""
Utilitaires pour la gestion audio (Speech-to-Text et Text-to-Speech).
"""

import io
import logging
from typing import Optional
import openai
from config import Config

logger = logging.getLogger(__name__)


class AudioManager:
    """Gestionnaire pour les opérations audio (STT et TTS)."""

    def __init__(self):
        """Initialise les clients audio."""
        self.groq_client = None
        self.openai_client = None
        self._initialize_clients()

    def _initialize_clients(self):
        """Initialise les clients Groq (STT) et OpenAI (TTS)."""
        try:
            logger.info("🎤 Initialisation des clients audio...")

            if not Config.GROQ_API_KEY or not Config.OPENAI_API_KEY:
                raise ValueError("Clés API audio manquantes")

            self.groq_client = openai.OpenAI(
                api_key=Config.GROQ_API_KEY,
                base_url=Config.GROQ_BASE_URL
            )
            self.openai_client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)

            logger.info("✅ Clients audio initialisés")

        except Exception as e:
            logger.error(f"❌ Erreur initialisation audio: {e}")
            raise

    def transcribe_audio(self, audio_bytes: bytes) -> Optional[str]:
        """
        Transcrit l'audio en texte.

        Args:
            audio_bytes: Bytes de l'audio à transcrire

        Returns:
            Texte transcrit ou None en cas d'erreur
        """
        if not self.groq_client:
            logger.error("Client Groq non initialisé")
            return None

        try:
            logger.info("🎤 Transcription audio...")
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = "recording.wav"

            transcription = self.groq_client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=audio_file
            )

            logger.info(f"✅ Transcription: {transcription.text[:100]}...")
            return transcription.text

        except Exception as e:
            logger.error(f"❌ Erreur transcription: {e}")
            return None

    def generate_audio(self, text: str) -> Optional[bytes]:
        """
        Génère l'audio à partir du texte.

        Args:
            text: Texte à convertir en audio

        Returns:
            Bytes audio ou None en cas d'erreur
        """
        if not self.openai_client:
            logger.error("Client OpenAI non initialisé")
            return None

        try:
            logger.info("🔊 Génération audio...")
            response = self.openai_client.audio.speech.create(
                model="tts-1",
                voice="nova",
                input=text
            )
            logger.info("✅ Audio généré")
            return response.content

        except Exception as e:
            logger.error(f"❌ Erreur génération audio: {e}")
            return None
