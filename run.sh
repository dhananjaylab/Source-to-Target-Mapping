#!/bin/bash

# Oracle Mapping Copilot — HuggingFace Spaces Entrypoint
# Runs both FastAPI backend and Streamlit frontend

echo "🚀 Starting Oracle Mapping Copilot..."

# Get the port from HF_SPACE_PORT environment variable or default to 7860
HF_SPACE_PORT=${HF_SPACE_PORT:-7860}

# Calculate backend port (use 8000 internally, HF Spaces will proxy)
BACKEND_PORT=8000

# Start FastAPI backend in background
echo "📡 Starting FastAPI backend on port $BACKEND_PORT..."
uvicorn main:app \
  --host 0.0.0.0 \
  --port $BACKEND_PORT \
  --reload \
  --log-level info &

BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start Streamlit frontend
echo "🎨 Starting Streamlit frontend on port $HF_SPACE_PORT..."
streamlit run app.py \
  --server.port=$HF_SPACE_PORT \
  --server.address=0.0.0.0 \
  --server.headless=true \
  --server.enableCORS=false \
  --logger.level=info

# Cleanup on exit
trap "kill $BACKEND_PID" EXIT
