# One image serving both the API and the built SPA.
#
# They cannot be split across two Render services: every API call in the app is
# a relative /api/... with credentials:'same-origin', so a separate frontend
# origin would never send the session cookie.

# ---- build the frontend ----------------------------------------------------
FROM node:22-slim AS web
WORKDIR /web
# Manifests first, so npm ci stays cached until dependencies actually change.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- resolve dependencies --------------------------------------------------
# `uv export` only reads uv.lock, it never builds an environment. That matters:
# backend/pyproject.toml sets python-preference = "only-managed" to work around a
# Windows issue, and `uv sync` would honour it and try to download a second
# interpreter into an image that already has one.
#
# The uv release image is distroless: it carries the binary and no shell, so a
# RUN step there fails with `exec: "/bin/sh": no such file or directory`. Copy
# the binary into an image that has one.
FROM python:3.12-slim AS deps
COPY --from=ghcr.io/astral-sh/uv:0.11.8 /uv /usr/local/bin/uv
WORKDIR /lock
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv export --no-dev --frozen --no-emit-project \
    --format requirements-txt --output-file /lock/requirements.txt

# ---- runtime ---------------------------------------------------------------
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app/backend
# The exported file carries hashes for every package, so pip verifies each one
# and the deployed dependency set is exactly the tested one.
COPY --from=deps /lock/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Bake the embedding model into the image. Chroma otherwise fetches it from
# HuggingFace on first use, which on a free-tier instance with no disk means a
# download on every cold start -- before the first search can return.
RUN python -c "from chromadb.utils import embedding_functions as ef; ef.DefaultEmbeddingFunction()(['warm the cache'])"

COPY backend/ ./
COPY --from=web /web/dist /app/frontend/dist

# render.yaml overrides CREDITWIZ_VAR_DIR when a persistent disk is attached.
ENV CREDITWIZ_VAR_DIR=/app/backend/var \
    CREDITWIZ_STATIC_DIR=/app/frontend/dist

EXPOSE 8000
# Render supplies $PORT; the default keeps `docker run -p 8000:8000` working.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
