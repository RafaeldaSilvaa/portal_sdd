#!/bin/bash
set -e
echo "=========================================="
echo "  EMASDEP v3.0 - Starting all services..."
echo "=========================================="

# Start Ollama in background
echo "[1/4] Starting Ollama..."
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready
echo "[2/4] Waiting for Ollama..."
for i in $(seq 1 30); do
  if curl -sf http://127.0.0.1:11434 > /dev/null 2>&1; then
    echo "  Ollama ready after ${i}s"
    break
  fi
  sleep 1
done

# Pull model in background (don't block startup)
echo "[3/4] Pulling llama3.2:1b model..."
ollama pull llama3.2:1b 2>&1 &

# Start backend (serves API + frontend static files)
echo "[4/4] Starting EMASDEP Portal..."
echo "=========================================="
echo "  Frontend: http://localhost:8000"
echo "  API:      http://localhost:8000/api"
echo "  Ollama:   http://localhost:11434"
echo "=========================================="

cd /app
exec python -m uvicorn emasdep.api.main:app --host 0.0.0.0 --port 8000 --log-level info
