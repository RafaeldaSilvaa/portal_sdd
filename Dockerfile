# EMASDEP v3.0 - Single container (Ollama + Backend + Frontend)
FROM node:20-alpine AS frontend
WORKDIR /app
COPY frontend/package.json ./
RUN npm install
COPY frontend/ .
ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM python:3.12-slim
WORKDIR /app

# Install Ollama
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://ollama.com/install.sh | sh && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Python deps
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/src/ src/
COPY backend/pyproject.toml .
RUN pip install --no-cache-dir -e .
COPY skills/ skills/

# Frontend build
COPY --from=frontend /app/dist /app/frontend

# Startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

ENV PYTHONUNBUFFERED=1
ENV EMASDEP_ENV=production
ENV OLLAMA_HOST=0.0.0.0
ENV EMASDEP_LLM_PROVIDER=ollama
ENV EMASDEP_LLM_MODEL=llama3.2:1b
ENV EMASDEP_LLM_BASE_URL=http://127.0.0.1:11434
ENV EMASDEP_DATABASE_PATH=/data/emasdep_portal.db

EXPOSE 8000

CMD ["/app/start.sh"]
