#!/bin/bash

# Oracle Mapping Copilot — HuggingFace Spaces Entrypoint
# Runs and supervises both FastAPI backend and Streamlit frontend

echo "🚀 Starting Oracle Mapping Copilot..."

# Get the port from HF_SPACE_PORT environment variable or default to 7860
HF_SPACE_PORT=${HF_SPACE_PORT:-7860}

# Calculate backend port (use 8000 internally, HF Spaces will proxy)
BACKEND_PORT=8000

# Cleanup handler to stop all background processes
cleanup() {
  echo "🛑 Stopping all background services..."
  if [ -n "$BACKEND_PID" ]; then
    kill "$BACKEND_PID" 2>/dev/null
  fi
  if [ -n "$STREAMLIT_PID" ]; then
    kill "$STREAMLIT_PID" 2>/dev/null
  fi
  exit 0
}

# Trap exit/termination signals early
trap cleanup EXIT SIGINT SIGTERM

# Start FastAPI backend in background (no --reload in production)
echo "📡 Starting FastAPI backend on port $BACKEND_PORT..."
uvicorn main:app \
  --host 0.0.0.0 \
  --port $BACKEND_PORT \
  --log-level info &

BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start Streamlit frontend in background
echo "🎨 Starting Streamlit frontend on port $HF_SPACE_PORT..."
streamlit run app.py \
  --server.port=$HF_SPACE_PORT \
  --server.address=0.0.0.0 \
  --server.headless=true \
  --server.enableCORS=false \
  --logger.level=info &

STREAMLIT_PID=$!

# Supervisor loop to monitor process health
echo "👀 Monitoring backend (PID: $BACKEND_PID) and frontend (PID: $STREAMLIT_PID)..."
while true; do
  # Check if backend is running
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "⚠️ FastAPI backend crashed! Restarting..."
    uvicorn main:app \
      --host 0.0.0.0 \
      --port $BACKEND_PORT \
      --log-level info &
    BACKEND_PID=$!
    sleep 2
  fi

  # Check if Streamlit is running
  if ! kill -0 "$STREAMLIT_PID" 2>/dev/null; then
    echo "⚠️ Streamlit frontend crashed! Restarting..."
    streamlit run app.py \
      --server.port=$HF_SPACE_PORT \
      --server.address=0.0.0.0 \
      --server.headless=true \
      --server.enableCORS=false \
      --logger.level=info &
    STREAMLIT_PID=$!
    sleep 2
  fi

  sleep 5
done
