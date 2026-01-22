#!/bin/bash
# AgriBot Startup Script
# เปิด Web Server สำหรับควบคุมหุ่นยนต์

set -e

# Configuration
PROJECT_DIR="/home/nww/Downloads/pro/project-robot"
VENV_DIR="${PROJECT_DIR}/.venv"
BACKEND_DIR="${PROJECT_DIR}/PI_WEBAPP/backend"
PORT=8000

echo "🚀 Starting AgriBot Web Server..."
echo "📁 Project: ${PROJECT_DIR}"

# Activate virtual environment
source "${VENV_DIR}/bin/activate"

# Change to backend directory
cd "${BACKEND_DIR}"

# Check if port is already in use
if lsof -i:${PORT} > /dev/null 2>&1; then
    echo "⚠️ Port ${PORT} is already in use"
    exit 1
fi

# Start server
echo "🌐 Starting on http://0.0.0.0:${PORT}"
exec uvicorn main:app --host 0.0.0.0 --port ${PORT}
