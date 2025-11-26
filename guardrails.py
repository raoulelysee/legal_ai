"""
Module de sécurité et guardrails pour l'application juridique.
Protection contre les prompt injections, abus, et requêtes malicieuses.
"""

import re
import logging
from typing import Tuple, Optional, List, Dict
from datetime import datetime, timedelta
from collections import defaultdict

from langchain_groq import ChatGroq
from config import Config

logger = logging.getLogger(__name__)


class SecurityGuardrails:
    """Système de guardrails multi-couches pour sécuriser l'application."""

    INJECTION_PATTERNS = [
        # Tentatives de modification du rôle/système
        r"(?i)(ignore|forget|disregard)\s+(all\s+)?(previous|above|prior|earlier)\s+(instructions?|prompts?|rules?|directives?)",
        r"(?i)you\s+are\s+(now|a)\s+(?!an?\s+assistant|an?\s+expert)",  # "you are now a hacker"
        r"(?i)(act|behave|pretend)\s+(as|like)\s+(?!an?\s+assistant|an?\s+expert)",
        r"(?i)system\s+(prompt|message|instruction|role)[:=\s]",
        r"(?i)new\s+(instructions?|rules?|role)[:=\s]",

        # Tentatives d'extraction de prompts/données
        r"(?i)(show|reveal|display|print|output|give\s+me)\s+(the\s+)?(system\s+)?(prompt|instruction|template)",
        r"(?i)what\s+(is|are)\s+your\s+(instructions?|prompts?|system\s+message)",
        r"(?i)(tell|show)\s+me\s+your\s+(base|system|original)\s+prompt",

        # Code injection
        r"<\s*script[^>]*>",  # <script>
        r"javascript\s*:",  # javascript:
        r"on(?:load|error|click|mouse)\s*=",  # onclick=, onload=
        r"eval\s*\(",  # eval(
        r"exec\s*\(",  # exec(

        # SQL injection
        r"(?i)(union|select|insert|update|delete|drop)\s+(all\s+)?(from|into|table)",
        r"(?i);\s*drop\s+table",
        r"(?i)'\s*or\s+'1'\s*=\s*'1",

        # Command injection
        r"&&|\|\||;|\$\(|\`",  # Shell operators
        r"(?i)(curl|wget|nc|netcat|bash|sh|cmd|powershell)\s+",

        # Jailbreak patterns
        r"(?i)jailbreak|dan\s+mode|dev\s+mode|god\s+mode",
        r"(?i)simulate|emulate\s+(?!a\s+legal\s+scenario)",
        r"(?i)(bypass|disable|turn\s+off|remove)\s+(safety|filter|guardrail|protection)",

        # Tentatives de manipulation contextuelle
        r"(?i)in\s+a\s+(hypothetical|fictional|alternate)\s+scenario",
        r"(?i)let'?s\s+pretend|what\s+if\s+you\s+were",
        r"(?i)role\s*play(ing)?[\s:]",
    ]

    # Mots-clés suspects (score de risque)
    SUSPICIOUS_KEYWORDS = {
        "ignore": 3,
        "disregard": 3,
        "forget": 3,
        "bypass": 4,
        "jailbreak": 5,
        "prompt": 2,
        "system": 2,
        "instruction": 2,
        "override": 4,
        "admin": 3,
        "root": 3,
        "execute": 3,
        "eval": 4,
        "script": 3,
    }

    # Longueurs maximales
    MAX_QUERY_LENGTH = 2000  # caractères
    MAX_WORD_COUNT = 300
    MIN_QUERY_LENGTH = 3

    # Rate limiting
    MAX_QUERIES_PER_MINUTE = 10
    MAX_QUERIES_PER_HOUR = 50

    def __init__(self):
        """Initialise le système de guardrails."""
        self.compiled_patterns = [re.compile(p) for p in self.INJECTION_PATTERNS]

        # Rate limiting storage (en mémoire)
        self.query_history: Dict[str, List[datetime]] = defaultdict(list)

        # LLM pour validation de contexte juridique
        self.llm = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=Config.GROQ_API_KEY,
            temperature=0,
            max_tokens=50
        )

        logger.info("✅ Guardrails de sécurité initialisés")

    def sanitize_input(self, text: str) -> str:
        """
        Nettoie et normalise l'entrée utilisateur.

        Args:
            text: Texte brut de l'utilisateur

        Returns:
            Texte nettoyé et sécurisé
        """
        if not text:
            return ""

        # Normalise les espaces
        text = " ".join(text.split())

        # Retire les caractères de contrôle dangereux
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

        # Encode/échappe les caractères spéciaux dangereux pour le HTML
        dangerous_chars = {
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#x27;',
            '&': '&amp;',
        }
        for char, escape in dangerous_chars.items():
            text = text.replace(char, escape)

        # Retire les multiples espaces
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    def detect_prompt_injection(self, query: str) -> Tuple[bool, Optional[str], int]:
        """
        Détecte les tentatives de prompt injection.

        Args:
            query: Requête utilisateur à analyser

        Returns:
            Tuple[bool, Optional[str], int]: (est_malicieux, raison, score_risque)
        """
        risk_score = 0
        reasons = []

        # 1. Vérification des patterns d'injection
        for i, pattern in enumerate(self.compiled_patterns):
            if pattern.search(query):
                risk_score += 5
                pattern_desc = self.INJECTION_PATTERNS[i][:50]
                reasons.append(f"Pattern d'injection détecté: {pattern_desc}")
                logger.warning(f"⚠️  Pattern d'injection #{i} détecté dans: {query[:100]}")

        # 2. Analyse des mots-clés suspects
        query_lower = query.lower()
        for keyword, score in self.SUSPICIOUS_KEYWORDS.items():
            if keyword in query_lower:
                risk_score += score
                reasons.append(f"Mot-clé suspect: '{keyword}'")

        # 3. Détection de multiples symboles spéciaux
        special_chars = len(re.findall(r'[<>{}()\[\]$`|;]', query))
        if special_chars > 10:
            risk_score += 3
            reasons.append(f"Trop de caractères spéciaux ({special_chars})")

        # 4. Détection de très longues lignes (potentiel payload)
        lines = query.split('\n')
        max_line_length = max(len(line) for line in lines) if lines else 0
        if max_line_length > 500:
            risk_score += 2
            reasons.append(f"Ligne très longue ({max_line_length} chars)")

        # 5. Répétitions suspectes (flood/spam)
        words = query_lower.split()
        if len(words) > 5:
            word_freq = defaultdict(int)
            for word in words:
                if len(word) > 3:  # Ignore petits mots
                    word_freq[word] += 1

            max_repetition = max(word_freq.values()) if word_freq else 0
            if max_repetition > len(words) * 0.3:  # > 30% de répétition
                risk_score += 3
                reasons.append(f"Répétition excessive détectée")

        # Seuils de décision
        is_malicious = risk_score >= 5
        reason = " | ".join(reasons) if reasons else None

        if is_malicious:
            logger.error(f"🚨 Tentative d'injection détectée! Score: {risk_score}, Raisons: {reason}")
            logger.error(f"   Query: {query[:200]}")

        return is_malicious, reason, risk_score

    def validate_query_length(self, query: str) -> Tuple[bool, Optional[str]]:
        """
        Valide la longueur de la requête.

        Args:
            query: Requête utilisateur

        Returns:
            Tuple[bool, Optional[str]]: (est_valide, message_erreur)
        """
        length = len(query)
        word_count = len(query.split())

        # Trop courte
        if length < self.MIN_QUERY_LENGTH:
            return False, f"❌ Requête trop courte (minimum {self.MIN_QUERY_LENGTH} caractères)"

        # Trop longue
        if length > self.MAX_QUERY_LENGTH:
            return False, f"❌ Requête trop longue (maximum {self.MAX_QUERY_LENGTH} caractères, vous avez {length})"

        # Trop de mots
        if word_count > self.MAX_WORD_COUNT:
            return False, f"❌ Trop de mots (maximum {self.MAX_WORD_COUNT} mots, vous avez {word_count})"

        return True, None

    def check_rate_limit(self, user_id: str = "default") -> Tuple[bool, Optional[str]]:
        """
        Vérifie le rate limiting pour prévenir les abus.

        Args:
            user_id: Identifiant de l'utilisateur (ou session)

        Returns:
            Tuple[bool, Optional[str]]: (est_autorisé, message_erreur)
        """
        now = datetime.now()

        # Nettoie l'historique ancien (> 1 heure)
        cutoff_time = now - timedelta(hours=1)
        self.query_history[user_id] = [
            t for t in self.query_history[user_id]
            if t > cutoff_time
        ]

        # Compte les requêtes récentes
        one_minute_ago = now - timedelta(minutes=1)
        queries_last_minute = sum(1 for t in self.query_history[user_id] if t > one_minute_ago)
        queries_last_hour = len(self.query_history[user_id])

        # Vérification limite par minute
        if queries_last_minute >= self.MAX_QUERIES_PER_MINUTE:
            return False, f"⏳ Trop de requêtes! Limite: {self.MAX_QUERIES_PER_MINUTE}/minute. Attendez quelques secondes."

        # Vérification limite par heure
        if queries_last_hour >= self.MAX_QUERIES_PER_HOUR:
            return False, f"⏳ Limite horaire atteinte! Maximum: {self.MAX_QUERIES_PER_HOUR}/heure. Revenez plus tard."

        # Enregistre cette requête
        self.query_history[user_id].append(now)

        logger.info(f"📊 Rate limit OK - User: {user_id}, Last minute: {queries_last_minute}, Last hour: {queries_last_hour}")

        return True, None

    def validate_legal_context(self, query: str) -> Tuple[bool, Optional[str]]:
        """
        Vérifie que la requête est dans un contexte juridique approprié via LLM.

        Utilise un LLM pour déterminer si la question est juridique ou non,
        au lieu de listes noires rigides qui peuvent bloquer des questions légitimes.

        Args:
            query: Requête utilisateur

        Returns:
            Tuple[bool, Optional[str]]: (est_légal_context, message)
        """
        try:
            # Prompt pour le LLM validateur
            validation_prompt = f"""Tu es un classificateur de questions juridiques. Ta seule tâche est de déterminer si une question concerne le DROIT (québécois ou canadien).

Réponds UNIQUEMENT par "OUI" ou "NON".

Réponds "OUI" si la question concerne:
- Le droit québécois (Code civil, lois provinciales, procédures, etc.)
- Le droit canadien fédéral (Code criminel, Constitution, Charte, immigration, etc.)
- Des aspects juridiques, légaux, réglementaires
- Des procédures judiciaires, tribunaux, avocats, notaires
- Des droits, obligations, responsabilités légales
- Même si la question mentionne des politiciens DANS UN CONTEXTE JURIDIQUE (ex: "Quels sont les pouvoirs juridiques du premier ministre?")

Réponds "NON" si la question concerne:
- La météo, le sport, la cuisine, le divertissement
- L'actualité politique générale (élections, partis)
- La technologie, la science pure
- Des sujets sans lien avec le droit

Question: "{query}"

Réponse (OUI ou NON):"""

            # Appelle le LLM
            response = self.llm.invoke(validation_prompt)
            answer = response.content.strip().upper()

            # Analyse la réponse
            if "OUI" in answer:
                logger.info(f"✅ Question juridique validée par LLM: {query[:100]}")
                return True, None
            else:
                logger.warning(f"❌ Question non-juridique détectée par LLM: {query[:100]}")
                return False, "❌ Je ne peux répondre qu'aux questions juridiques concernant le droit québécois ou canadien. Votre question ne semble pas porter sur un sujet juridique."

        except Exception as e:
            logger.error(f"⚠️ Erreur validation LLM: {e}. Fallback vers validation permissive.")
            # En cas d'erreur, on accepte (fail-open) pour ne pas bloquer les utilisateurs
            return True, None

    def full_validation(self, query: str, user_id: str = "default") -> Tuple[bool, Optional[str]]:
        """
        Validation complète multi-couches d'une requête.

        Args:
            query: Requête utilisateur brute
            user_id: Identifiant utilisateur pour rate limiting

        Returns:
            Tuple[bool, Optional[str]]: (est_valide, message_erreur_ou_warning)
        """
        logger.info(f"🔒 Validation complète de la requête (user: {user_id})")

        # 1. Vérification longueur
        is_valid_length, length_msg = self.validate_query_length(query)
        if not is_valid_length:
            logger.warning(f"❌ Longueur invalide: {length_msg}")
            return False, length_msg

        # 2. Rate limiting
        is_rate_ok, rate_msg = self.check_rate_limit(user_id)
        if not is_rate_ok:
            logger.warning(f"❌ Rate limit: {rate_msg}")
            return False, rate_msg

        # 3. Détection prompt injection
        is_injection, injection_reason, risk_score = self.detect_prompt_injection(query)
        if is_injection:
            logger.error(f"🚨 PROMPT INJECTION détectée! Score: {risk_score}")
            return False, f"🚨 Requête rejetée pour des raisons de sécurité. {injection_reason}"

        # 4. Validation contexte juridique
        is_legal, legal_msg = self.validate_legal_context(query)
        if not is_legal:
            logger.warning(f"❌ Contexte non-juridique: {legal_msg}")
            return False, legal_msg

        # 5. Warning si score de risque modéré (mais pas rejeté)
        if risk_score > 2:
            logger.warning(f"⚠️  Score de risque modéré ({risk_score}), mais requête acceptée")

        logger.info(f"✅ Validation complète réussie (score risque: {risk_score})")
        return True, None


# Instance globale singleton
_guardrails_instance = None


def get_guardrails() -> SecurityGuardrails:
    """Retourne l'instance singleton des guardrails."""
    global _guardrails_instance
    if _guardrails_instance is None:
        _guardrails_instance = SecurityGuardrails()
    return _guardrails_instance
