# Dockerfile pour l'application Network Monitor
# Projet d'Examen DEVNET - L3 RI ISI Keur Massar

FROM python:3.11-slim

# Configuration des métadonnées
LABEL maintainer="ISAAC L3 RI ISI Keur Massar"
LABEL description="Application Flask de monitoring réseau distribué"
LABEL version="1.0"

# Définition du répertoire de travail
WORKDIR /app

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copie des fichiers de dépendances
COPY requirements.txt .

# Installation des dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copie des fichiers de l'application
COPY app.py .
COPY templates/ ./templates/

# Création d'un utilisateur non-root pour la sécurité
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Exposition du port
EXPOSE 5000

# Variables d'environnement par défaut
ENV PYTHONPATH=/app
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Commande de démarrage
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:app"]
