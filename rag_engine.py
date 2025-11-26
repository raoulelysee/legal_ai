"""
Moteur RAG (Retrieval-Augmented Generation) pour les questions juridiques.
"""

import re
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pinecone import Pinecone
from tavily import TavilyClient

from config import Config
from guardrails import get_guardrails

logger = logging.getLogger(__name__)


class ImprovedFusionRAGQuery:
    """Moteur RAG amélioré avec fusion de sources multiples."""

    def __init__(self):
        """Initialise le moteur RAG avec gestion d'erreurs robuste."""
        logger.info("Initialisation du moteur FusionRAG amélioré...")

        # Valide la configuration
        Config.validate()

        # Initialise les composants
        self._init_pinecone()
        self._init_embeddings()
        self._init_expander_llm()
        self._init_synthesizer_llm()
        self._init_tavily()
        self._init_prompts()

        logger.info("✅ Moteur FusionRAG amélioré initialisé avec succès")

    def _init_pinecone(self):
        """Initialise la connexion Pinecone."""
        try:
            self.pc = Pinecone(api_key=Config.PINECONE_API_KEY)
            self.index_name = Config.PINECONE_INDEX_NAME
            self.namespace = Config.PINECONE_NAMESPACE
            self.index = self.pc.Index(self.index_name)

            logger.info(f"✅ Pinecone connecté - Index: {self.index_name}, Namespace: {self.namespace}")
        except Exception as e:
            logger.error(f"❌ Erreur Pinecone: {e}")
            raise

    def _init_embeddings(self):
        """Initialise le modèle d'embeddings."""
        try:
            self.embeddings = OpenAIEmbeddings(
                model=Config.EMBEDDING_MODEL,
                openai_api_key=Config.OPENAI_API_KEY
            )
            logger.info("✅ Embeddings OpenAI initialisés")
        except Exception as e:
            logger.error(f"❌ Erreur Embeddings: {e}")
            raise

    def _init_expander_llm(self):
        """Initialise le LLM pour l'expansion de requêtes."""
        try:
            self.llm_expander = ChatOpenAI(
                model=Config.EXPANDER_MODEL,
                temperature=0.3,
                openai_api_key=Config.GROQ_API_KEY,
                base_url=Config.GROQ_BASE_URL
            )
            logger.info(f"✅ LLM Expander ({Config.EXPANDER_MODEL}) initialisé")
        except Exception as e:
            logger.error(f"❌ Erreur LLM Expander: {e}")
            raise

    def _init_synthesizer_llm(self):
        """Initialise le LLM pour la synthèse."""
        try:
            self.llm_synthesizer = ChatOpenAI(
                model=Config.SYNTHESIZER_MODEL,
                temperature=0,
                openai_api_key=Config.GROQ_API_KEY,
                base_url=Config.GROQ_BASE_URL
            )
            logger.info(f"✅ LLM Synthesizer ({Config.SYNTHESIZER_MODEL}) initialisé")
        except Exception as e:
            logger.error(f"❌ Erreur LLM Synthesizer: {e}")
            raise

    def _init_tavily(self):
        """Initialise le client Tavily."""
        try:
            self.tavily_client = TavilyClient(api_key=Config.TAVILY_API_KEY)
            logger.info("✅ Client Tavily initialisé")
        except Exception as e:
            logger.error(f"❌ Erreur Tavily: {e}")
            raise

    def _init_prompts(self):
        """Initialise les templates de prompts."""
        self.expansion_prompt = ChatPromptTemplate.from_template(
"""Tu es un expert en recherche juridique québécoise.

Génère 5 requêtes de recherche alternatives pour trouver l'information dans une base de données juridique.

**RÈGLES IMPORTANTES:**
1. Utilise des termes juridiques précis du Québec
2. Inclus des variations avec numéros d'articles si pertinent
3. Reformule avec synonymes juridiques
4. Pense aux codes pertinents (C.c.Q., C.p.c., Code criminel, etc.)
5. Considère les concepts juridiques connexes

**EXEMPLES DE BONNES REQUÊTES:**
- Question: "Comment divorcer au Québec?"
  Requêtes:
  1. divorce procédure Québec conditions
  2. dissolution mariage Code civil Québec
  3. séparation légale conjoints articles 516-521 CCQ
  4. rupture union matrimoniale formalités
  5. fin mariage divorce contentieux

**Question de l'utilisateur:** {question}

**Génère UNIQUEMENT 5 requêtes, une par ligne, sans numérotation:**
"""
        )

        self.synthesis_prompt = ChatPromptTemplate.from_template(
f"""Tu es un assistant juridique expert spécialisé dans le droit québécois.

**MISSION:** Répondre aux questions juridiques en te basant STRICTEMENT sur les documents fournis.

**CONTEXTE DE LA QUESTION:**
- Région: Québec, Canada (PAS la France, PAS les USA)
- Sources: Base de données juridique interne + Web (si nécessaire)

**RÈGLES STRICTES (GUARDRAILS):**

1. **PRIORITÉ AUX SOURCES:**
   - TOUJOURS privilégier le CONTEXTE VÉRIFIÉ (base de données interne)
   - N'utiliser le CONTEXTE WEB que si le contexte vérifié est insuffisant
   - Si tu utilises le web, MENTIONNE-LE clairement: "Selon une source web..."

2. **CITATIONS OBLIGATOIRES:**
   - TOUJOURS citer les sources avec précision
   - Format: "Selon l'Article X du [Nom du document]..."
   - Mentionne les numéros d'articles, de lois, de codes

3. **RÉPONSE STRUCTURÉE:**
   - Commence par un résumé direct (1-2 phrases)
   - Développe avec les détails pertinents
   - Cite les articles et sources spécifiques
   - Termine par le disclaimer obligatoire

4. **QUALITÉ DE LA RÉPONSE:**
   - Sois précis et factuel
   - N'invente RIEN
   - Si l'info n'est pas dans le contexte: "Désolé, je n'ai pas trouvé l'information pertinente dans les documents fournis."
   - Ne fournis AUCUN conseil juridique personnel

5. **HORS-SUJET:**
   - Réponds UNIQUEMENT aux questions juridiques
   - Pour toute autre question: "Je ne peux aider qu'avec des questions juridiques."

**FORMAT DE RÉPONSE ATTENDU:**

**Réponse directe:** [1-2 phrases résumant la réponse]

**Détails:**
[Développement avec citations précises]

**Sources:**
- [Source 1 avec article/section]
- [Source 2 avec article/section]

{Config.LEGAL_DISCLAIMER}

---

**CONTEXTE VÉRIFIÉ (Base de données juridique interne):**
{{context_pinecone}}

---

**CONTEXTE WEB (Internet - utiliser avec prudence):**
{{context_web}}

---

**QUESTION DE L'UTILISATEUR:**
{{question}}

---

**RÉPONSE (en respectant TOUTES les règles):**
"""
        )

    def extract_legal_entities(self, text: str) -> List[str]:
        """Extrait les entités juridiques de la question."""
        entities = []

        # Articles (ex: "article 1457", "art. 2847")
        article_patterns = [
            r'(?:article|art\.?)\s*(\d+(?:\.\d+)?)',
            r'(?:articles|art\.?)\s*(\d+)\s*(?:à|et)\s*(\d+)'
        ]
        for pattern in article_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                entities.append(f"article {match.group(1)}")

        # Codes juridiques
        codes = [
            "Code civil du Québec", "C.c.Q.", "CCQ",
            "Code de procédure civile", "C.p.c.", "CPC",
            "Code criminel", "C.cr.",
            "Charte des droits et libertés"
        ]
        for code in codes:
            if code.lower() in text.lower():
                entities.append(code)

        # Concepts juridiques courants
        concepts = [
            "contrat", "responsabilité", "divorce", "testament",
            "succession", "bail", "hypothèque", "servitude",
            "prescription", "délai", "recours", "dommages"
        ]
        for concept in concepts:
            if concept in text.lower():
                entities.append(concept)

        logger.info(f"🔍 Entités extraites: {entities}")
        return entities

    def generate_queries(self, user_question: str) -> List[str]:
        """Génère des requêtes alternatives améliorées."""
        try:
            logger.info("🤖 Génération de requêtes alternatives améliorées...")

            # Extraction d'entités pour enrichir
            entities = self.extract_legal_entities(user_question)

            # Détection spéciale pour articles spécifiques
            article_match = re.search(r'(?:article|art\.?)\s*(\d+)', user_question, re.IGNORECASE)

            queries = []

            # Si un article spécifique est demandé, génère des requêtes ciblées
            if article_match:
                article_num = article_match.group(1)
                logger.info(f"🎯 Article spécifique détecté: {article_num}")

                # Requêtes ultra-ciblées pour articles
                queries = [
                    user_question,
                    f"article {article_num}",
                    f"art. {article_num}",
                    f"article {article_num} CCQ",
                    f"article {article_num} Code civil Québec",
                    f"responsabilité article {article_num}",
                    f"faute article {article_num}",
                    f"obligation article {article_num}",
                    f"dommages article {article_num}",
                    f"responsabilité civile extracontractuelle"
                ]
            else:
                # Génération normale avec le LLM pour les questions générales
                chain = self.expansion_prompt | self.llm_expander | StrOutputParser()
                response = chain.invoke({"question": user_question})

                # Nettoie et filtre les requêtes
                queries = [q.strip() for q in response.strip().split('\n') if q.strip() and len(q.strip()) > 10]

                # Retire la numérotation si présente
                queries = [re.sub(r'^[\d\-\.\)]+\s*', '', q) for q in queries]

                # Ajoute la question originale en premier
                queries = [user_question] + queries[:5]

                # Si des entités ont été trouvées, ajoute une requête avec toutes les entités
                if entities:
                    entity_query = " ".join(entities[:5])
                    queries.append(entity_query)

            # Déduplique
            seen = set()
            unique_queries = []
            for q in queries:
                q_lower = q.lower()
                if q_lower not in seen:
                    seen.add(q_lower)
                    unique_queries.append(q)

            logger.info(f"✅ {len(unique_queries)} requêtes générées:")
            for i, q in enumerate(unique_queries, 1):
                logger.info(f"   {i}. {q[:80]}...")

            return unique_queries[:10]

        except Exception as e:
            logger.error(f"❌ Erreur génération requêtes: {e}")
            return [user_question]

    async def search_pinecone_async(self, query: str) -> List[Dict[str, Any]]:
        """Recherche asynchrone dans Pinecone."""
        try:
            # Détection d'article spécifique dans la requête
            article_match = re.search(r'(?:article|art\.?)\s*(\d+)', query, re.IGNORECASE)

            query_embedding = await asyncio.to_thread(
                self.embeddings.embed_query, query
            )

            search_kwargs = {
                "vector": query_embedding,
                "top_k": 20,
                "include_metadata": True
            }

            # Filtre par métadonnées si article spécifique détecté
            if article_match:
                article_num = article_match.group(1)
                search_kwargs["filter"] = {
                    "article_num": {"$eq": article_num}
                }
                logger.info(f"🎯 Recherche avec filtre métadonnées: article_num = '{article_num}'")

            if self.namespace:
                search_kwargs["namespace"] = self.namespace

            results = await asyncio.to_thread(
                self.index.query,
                **search_kwargs
            )

            matches = results.get('matches', [])

            # Log résultats avant filtrage
            if matches:
                logger.info(f"   Query: '{query[:50]}...' → {len(matches)} résultats bruts:")
                for i, m in enumerate(matches[:5], 1):
                    score = m.get('score', 0)
                    metadata = m.get('metadata', {})
                    source = metadata.get('source', metadata.get('filename', 'Inconnu'))
                    logger.info(f"      {i}. Score: {score:.4f} | {source[:50]}")

            # Filtrage par score de similarité
            filtered_matches = [
                m for m in matches
                if m.get('score', 0) >= Config.MIN_SIMILARITY_SCORE
            ]

            logger.info(f"   → Après filtre (≥{Config.MIN_SIMILARITY_SCORE}): {len(filtered_matches)} résultats gardés")

            return filtered_matches

        except Exception as e:
            logger.error(f"❌ Erreur recherche Pinecone pour '{query[:50]}...': {e}")
            return []

    async def get_pinecone_context_async(self, queries: List[str]) -> Tuple[str, List[Dict]]:
        """Récupère le contexte Pinecone en parallèle."""
        logger.info(f"🔎 Recherche Pinecone avec {len(queries)} requêtes...")

        try:
            # Recherches en parallèle
            tasks = [self.search_pinecone_async(q) for q in queries]
            all_results = await asyncio.gather(*tasks)

            # Déduplique les résultats par ID
            all_matches = [match for sublist in all_results for match in sublist]
            unique_chunks_dict = {match['id']: match for match in all_matches}
            unique_chunks = list(unique_chunks_dict.values())

            # Trie par score de similarité (décroissant)
            unique_chunks.sort(key=lambda x: x.get('score', 0), reverse=True)

            # Formate le contexte
            context_parts = []
            chunks_info = []
            total_chars = 0

            for i, chunk in enumerate(unique_chunks):
                metadata = chunk.get('metadata', {})
                text = metadata.get('text', '')
                source = metadata.get('source', metadata.get('filename', 'Inconnue'))
                article = metadata.get('article', 'N/A')
                score = chunk.get('score', 0)

                part = f"""Source: {source}
Article/Section: {article}
Score de pertinence: {score:.2f}
Texte: {text}"""

                # Limite la longueur totale
                if total_chars + len(part) > Config.MAX_CONTEXT_TOKENS:
                    logger.info(f"   ⚠️  Limite de contexte atteinte ({Config.MAX_CONTEXT_TOKENS} chars), arrêt à {i+1} chunks")
                    break

                context_parts.append(part)
                chunks_info.append({
                    'source': source,
                    'article': article,
                    'score': score,
                    'text': text[:200]
                })
                total_chars += len(part)

            context_text = "\n\n---\n\n".join(context_parts)

            logger.info(f"✅ Contexte Pinecone: {len(context_parts)} chunks, {total_chars} caractères")
            logger.info(f"   Top 3 sources:")
            for i, info in enumerate(chunks_info[:3], 1):
                logger.info(f"      {i}. {info['source']} (score: {info['score']:.2f})")

            return context_text, chunks_info

        except Exception as e:
            logger.error(f"❌ Erreur get_pinecone_context: {e}")
            return "", []

    def get_pinecone_context(self, queries: List[str]) -> Tuple[str, List[Dict]]:
        """Version synchrone wrapper."""
        return asyncio.run(self.get_pinecone_context_async(queries))

    def get_web_context(self, queries: List[str]) -> str:
        """Recherche sur le web avec Tavily."""
        logger.info("🌐 Recherche web (Tavily)...")
        all_web_context = []

        # Limite à 2 requêtes pour réduire les coûts
        queries_to_web = queries[:2]

        try:
            for query in queries_to_web:
                # Enrichit la requête pour cibler le Québec
                quebec_query = f"{query} Québec Canada"

                response = self.tavily_client.search(
                    query=quebec_query,
                    search_depth="advanced",
                    max_results=3
                )

                for result in response.get('results', []):
                    content = result.get('content', '')[:600]
                    title = result.get('title', 'Sans titre')
                    all_web_context.append(
                        f"Source: {result['url']}\nTitre: {title}\nTexte: {content}"
                    )

            logger.info(f"✅ Contexte Web: {len(all_web_context)} résultats")
            return "\n\n---\n\n".join(all_web_context)

        except Exception as e:
            logger.error(f"❌ Erreur recherche web: {e}")
            return ""

    def synthesize_answer(self, context_pinecone: str, context_web: str, question: str, chunks_info: List[Dict]) -> str:
        """Synthétise la réponse finale."""
        try:
            logger.info("✍️  Synthèse de la réponse...")

            chain = self.synthesis_prompt | self.llm_synthesizer | StrOutputParser()

            answer = chain.invoke({
                "context_pinecone": context_pinecone,
                "context_web": context_web,
                "question": question
            })

            # Vérifie que le disclaimer est présent
            if Config.LEGAL_DISCLAIMER not in answer:
                answer += f"\n\n{Config.LEGAL_DISCLAIMER}"

            # Ajoute un résumé des sources en bas
            if chunks_info:
                answer += "\n\n**📚 Sources consultées:**\n"
                seen_sources = set()
                for chunk in chunks_info[:5]:
                    source = chunk['source']
                    if source not in seen_sources:
                        seen_sources.add(source)
                        answer += f"- {source} (pertinence: {chunk['score']:.0%})\n"

            logger.info("✅ Réponse générée avec succès")
            return answer

        except Exception as e:
            logger.error(f"❌ Erreur synthèse: {e}")
            return f"Désolé, une erreur s'est produite lors de la génération de la réponse.\n\n{Config.LEGAL_DISCLAIMER}"

    def query(self, user_question: str, user_id: str = "default") -> Tuple[str, Dict[str, bool]]:
        """
        Fonction principale de requête avec guardrails de sécurité.

        Args:
            user_question: Question de l'utilisateur
            user_id: Identifiant utilisateur pour rate limiting

        Returns:
            Tuple[str, Dict]: (réponse, metadata sur les sources utilisées)
        """
        try:
            logger.info(f"📝 Nouvelle requête: {user_question[:100]}...")

            # 🔒 GUARDRAILS - Validation complète de sécurité
            guardrails = get_guardrails()

            # Validation avec detection d'injection, rate limiting, etc.
            is_valid, error_msg = guardrails.full_validation(user_question, user_id)

            if not is_valid:
                logger.error(f"🚨 Requête invalide rejetée: {error_msg}")
                return (
                    f"{error_msg}\n\n{Config.LEGAL_DISCLAIMER}",
                    {"used_pinecone": False, "used_web": False, "blocked": True, "reason": error_msg}
                )

            # Sanitize l'input après validation
            sanitized_question = guardrails.sanitize_input(user_question)
            logger.info(f"✅ Requête validée et sanitizée")

            # 1. Générer les requêtes améliorées (utiliser la version sanitized)
            queries = self.generate_queries(sanitized_question)

            # 2. Récupérer le contexte Pinecone avec métadonnées
            context_pinecone, chunks_info = self.get_pinecone_context(queries)

            # 3. Décider si la recherche web est nécessaire
            needs_web = len(context_pinecone) < Config.MIN_CONTEXT_LENGTH
            context_web = ""

            if needs_web:
                logger.info("⚠️  Contexte Pinecone insuffisant, recherche web activée")
                context_web = self.get_web_context(queries)
            else:
                logger.info("✅ Contexte Pinecone suffisant, pas de recherche web")

            # 4. Vérifier qu'on a au moins un contexte
            if not context_pinecone and not context_web:
                logger.warning("⚠️  Aucun contexte trouvé")
                return (
                    f"Désolé, je n'ai pas trouvé l'information pertinente dans la base de données ou sur le web pour répondre à cette question.\n\n{Config.LEGAL_DISCLAIMER}",
                    {"used_pinecone": False, "used_web": False}
                )

            # 5. Synthétiser la réponse (utiliser la version sanitized)
            answer = self.synthesize_answer(context_pinecone, context_web, sanitized_question, chunks_info)

            # 6. Métadonnées enrichies
            metadata = {
                "used_pinecone": bool(context_pinecone),
                "used_web": bool(context_web),
                "chunks_found": len(chunks_info),
                "queries_generated": len(queries)
            }

            logger.info(f"✅ Requête complétée - Pinecone: {metadata['used_pinecone']}, Web: {metadata['used_web']}, Chunks: {metadata['chunks_found']}")

            return answer, metadata

        except Exception as e:
            logger.error(f"❌ Erreur critique dans query(): {e}", exc_info=True)
            return (
                f"Désolé, une erreur technique s'est produite. Veuillez réessayer.\n\n{Config.LEGAL_DISCLAIMER}",
                {"used_pinecone": False, "used_web": False, "error": True}
            )
