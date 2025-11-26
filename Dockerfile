# Utiliser une image Python de base
FROM python:3.10-slim

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# --- NOUVELLE LIGNE ---
# Installer les dépendances système (PortAudio pour le micro)
RUN apt-get update && apt-get install -y portaudio19-dev

# Copier le fichier des dépendances
COPY requirements.txt ./

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier tout le reste de ton code (ton app.py)
COPY . .

# Exposer le port par défaut de Streamlit
EXPOSE 8501

# Commande pour lancer l'application Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]