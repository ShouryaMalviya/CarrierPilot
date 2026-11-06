#!/usr/bin/env bash
# ==============================================================================
# CareerPilot AI — Local Development Environment Startup Script (Bash)
# ==============================================================================

set -e

echo "=========================================================="
echo " CareerPilot AI — Launching Local Development Services    "
echo "=========================================================="

# 1. Check Python Virtualenv
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "[ERROR] Virtual environment .venv not found."
    exit 1
fi

# 2. Seed Demo Environment
echo -e "\n[1/3] Ensuring Database Migrations and Demo Benchmark State..."
python scripts/seed_demo_environment.py

# 3. Launch Backend
echo -e "\n[2/3] Launching FastAPI Backend on http://127.0.0.1:8000..."
(cd backend && uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload) &
BACKEND_PID=$!

# Trap exit to cleanup background backend process
cleanup() {
    echo "Shutting down CareerPilot AI..."
    kill $BACKEND_PID 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# 4. Launch Frontend
echo -e "\n[3/3] Launching Vite Frontend on http://localhost:5173..."
npm --prefix frontend run dev
