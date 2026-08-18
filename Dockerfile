# Image de production C-Lab.
#
# Le front (frontend/dist) est construit EN LOCAL puis copié tel quel :
# on ne fait pas tourner Metro/Expo dans le conteneur. Metro demande 1 à
# 2 Go de RAM, ce qui dépasse les quotas de build des offres d'entrée de
# gamme (Railway free : 0,5 Go) et ferait échouer le déploiement.
#
#   Avant chaque déploiement :
#     cd frontend && yarn expo export -p web
#
# Résultat : une image légère qui ne contient que Python + le backend +
# les fichiers statiques déjà compilés.

FROM python:3.12-slim

# - PYTHONDONTWRITEBYTECODE : pas de .pyc dans l'image
# - PYTHONUNBUFFERED : les logs sortent immédiatement (utile en PaaS)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Dépendances d'abord : cette couche est mise en cache tant que
# requirements.txt ne change pas.
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Backend (inclut strlib_repo, le moteur de calcul).
COPY backend/ ./backend/

# Front déjà compilé — servi par FastAPI avec repli SPA.
COPY frontend/dist/ ./frontend/dist/

# Exécution sans privilèges.
RUN useradd --create-home --uid 10001 clab && chown -R clab:clab /app
USER clab

WORKDIR /app/backend

EXPOSE 8000

# La plupart des PaaS injectent $PORT : on s'y conforme, avec 8000 par défaut.
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}"]
