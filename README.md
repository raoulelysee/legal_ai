# ⚖️ Encyclopédie Juridique du Québec

Application web interactive utilisant l'IA pour répondre aux questions juridiques concernant le droit québécois et canadien.

## 🚀 Fonctionnalités

- **🔍 Recherche intelligente** : Fusion de sources multiples (base de données vectorielle + web)
- **🤖 IA avancée** : Utilise des modèles LLM de pointe (Llama 3.3 70B)
- **🎤 Support vocal** : Entrée et sortie audio (Speech-to-Text et Text-to-Speech)
- **📚 Citations précises** : Références aux articles de loi et sources
- **🔐 Protection** : Système optionnel de mot de passe pour éviter l'usage abusif
- **⚡ Performance** : Recherches parallèles et cache intelligent

## 📋 Prérequis

- Python 3.8+
- Clés API pour :
  - OpenAI (embeddings et TTS)
  - Groq (LLM et transcription audio)
  - Pinecone (base de données vectorielle)
  - Tavily (recherche web)

## 🛠️ Installation

### 1. Cloner le projet

```bash
git clone <votre-repo>
cd encyclopedie_juridique
```

### 2. Créer un environnement virtuel

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configuration

1. **Copier le fichier d'exemple**
   ```bash
   cp .env.example .env
   ```

2. **Éditer le fichier `.env`** avec vos clés API :

```env
# OpenAI (obligatoire)
OPENAI_API_KEY=sk-...

# Pinecone (obligatoire)
PINECONE_API_KEY=pcsk_...
PINECONE_INDEX_NAME=votre_index
PINECONE_NAMESPACE=juridique_v2

# Groq (obligatoire)
GROQ_API_KEY=gsk_...

# Tavily (obligatoire pour recherche web)
TAVILY_API_KEY=tvly-...

# Protection (optionnel)
ENABLE_PASSWORD_PROTECTION=true
APP_PASSWORD=VotreMotDePasse123!
```

### 5. Obtenir les clés API

#### OpenAI
1. Visitez [platform.openai.com](https://platform.openai.com/api-keys)
2. Créez une nouvelle clé API
3. Copiez-la dans `.env`

#### Groq
1. Visitez [console.groq.com](https://console.groq.com/keys)
2. Créez un compte gratuit
3. Générez une clé API
4. Copiez-la dans `.env`

#### Pinecone
1. Visitez [app.pinecone.io](https://app.pinecone.io/)
2. Créez un compte gratuit
3. Créez un index (dimensions: 1536, metric: cosine)
4. Copiez la clé API et le nom de l'index dans `.env`

#### Tavily
1. Visitez [tavily.com](https://tavily.com/)
2. Créez un compte
3. Générez une clé API
4. Copiez-la dans `.env`

## 🚀 Lancement

### Version sécurisée (recommandée)
```bash
streamlit run app_secure.py
```

### Version originale
```bash
streamlit run app_improved.py
```

L'application sera accessible sur [http://localhost:8501](http://localhost:8501)

## 📁 Structure du projet

```
encyclopedie_juridique/
├── app_secure.py           # Application Streamlit sécurisée (nouvelle version)
├── app_improved.py         # Application originale
├── config.py               # Configuration centralisée
├── rag_engine.py          # Moteur RAG (recherche et génération)
├── audio_utils.py         # Utilitaires audio (STT/TTS)
├── .env                   # Variables d'environnement (NE PAS PARTAGER)
├── .env.example           # Exemple de configuration
├── .gitignore             # Fichiers à ignorer par Git
├── requirements.txt       # Dépendances Python
└── README.md             # Ce fichier
```

## 🔒 Sécurité

### ⚠️ IMPORTANT

**NE JAMAIS partager votre fichier `.env` !**

Il contient vos clés API secrètes. Le fichier `.gitignore` est configuré pour l'exclure automatiquement de Git.

### Protection par mot de passe

Pour activer la protection de l'application :

1. Dans `.env`, définissez :
   ```env
   ENABLE_PASSWORD_PROTECTION=true
   APP_PASSWORD=VotreMotDePasseComplexe!
   ```

2. Les utilisateurs devront entrer le mot de passe pour accéder à l'application

### Pour Hugging Face Spaces

1. **NE PAS** téléverser le fichier `.env`
2. Configurez les secrets dans : `Settings > Repository secrets`
3. Ajoutez chaque variable d'environnement individuellement

## 🎯 Utilisation

### Interface texte
1. Tapez votre question juridique dans la barre de saisie
2. Cliquez sur "Envoyer" ou appuyez sur Entrée
3. L'IA analyse votre question et génère une réponse avec citations

### Interface vocale
1. Cliquez sur l'icône 🎤 pour commencer l'enregistrement
2. Parlez clairement
3. Cliquez sur ⏹️ pour arrêter
4. La transcription s'affiche et l'IA répond en audio

### Exemples de questions

- "Quelles sont les conditions de validité d'un contrat au Québec ?"
- "Expliquez-moi l'article 1457 du Code civil du Québec"
- "Comment fonctionne le divorce au Québec ?"
- "Quels sont les délais de prescription pour un recours civil ?"

## ⚙️ Configuration avancée

### Ajuster les paramètres de recherche

Dans `.env`, vous pouvez modifier :

```env
# Score minimal de similarité (0.0 à 1.0)
MIN_SIMILARITY_SCORE=0.55

# Taille maximale du contexte (en caractères)
MAX_CONTEXT_TOKENS=12000

# Longueur minimale du contexte Pinecone
MIN_CONTEXT_LENGTH=100

# Modèles LLM
EXPANDER_MODEL=llama-3.3-70b-versatile
SYNTHESIZER_MODEL=llama-3.3-70b-versatile
```

## 🐛 Dépannage

### Erreur "Clés API manquantes"
- Vérifiez que toutes les clés sont bien définies dans `.env`
- Vérifiez qu'il n'y a pas d'espaces avant/après les clés
- Relancez l'application

### Erreur Pinecone
- Vérifiez que l'index existe dans votre compte Pinecone
- Vérifiez que le namespace est correct
- Vérifiez que l'index a bien 1536 dimensions

### Erreur audio
- Vérifiez que les clés Groq et OpenAI sont valides
- Vérifiez votre connexion internet
- Essayez de désactiver temporairement l'audio

### Logs
Les logs sont disponibles dans le fichier `app.log`

## 📝 Notes importantes

### Disclaimer juridique
Cette application fournit des informations à caractère général et ne constitue **PAS** un conseil juridique professionnel.

Consultez toujours un avocat ou un notaire pour obtenir des conseils adaptés à votre situation spécifique.

### Limitations
- L'IA peut faire des erreurs
- Les réponses sont basées sur les documents disponibles
- Certaines informations peuvent être obsolètes
- Ne remplace pas une consultation juridique

## 🚀 Déploiement sur Hugging Face Spaces

1. Créez un nouveau Space sur [huggingface.co/spaces](https://huggingface.co/spaces)
2. Sélectionnez "Streamlit" comme SDK
3. Téléversez tous les fichiers **SAUF** `.env`
4. Dans Settings > Repository secrets, ajoutez :
   - `OPENAI_API_KEY`
   - `PINECONE_API_KEY`
   - `PINECONE_INDEX_NAME`
   - `PINECONE_NAMESPACE`
   - `GROQ_API_KEY`
   - `TAVILY_API_KEY`
   - `ENABLE_PASSWORD_PROTECTION` (optionnel)
   - `APP_PASSWORD` (si protection activée)

5. Créez un fichier `.streamlit/config.toml` pour la configuration Streamlit

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 👨‍💻 Auteur

Créé avec ❤️ par [Votre Nom]

## 🤝 Contributions

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.

---

**⚠️ Rappel de sécurité**
- Ne jamais partager vos clés API
- Ne jamais committer le fichier `.env`
- Utilisez la protection par mot de passe sur les déploiements publics
- Surveillez l'utilisation de vos API pour détecter tout usage abusif
