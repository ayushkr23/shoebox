#!/usr/bin/env bash
# Shoebox - Local Receipt Scanner & Organizer
# Starts FastAPI server on http://localhost:8000

set -e

PORT=${PORT:-8000}
HOST=${HOST:-"0.0.0.0"}
MODEL_NAME=${MODEL_NAME:-"gemma3:4b"}
OLLAMA_HOST=${OLLAMA_HOST:-"http://localhost:11434"}

echo "=========================================================="
echo "  SHOEBOX: 100% LOCAL RECEIPT PHOTO TO CLEAN SPREADSHEET"
echo "=========================================================="
echo "Model configured : ${MODEL_NAME}"
echo "Ollama Endpoint  : ${OLLAMA_HOST}"
echo "Web UI URL       : http://localhost:${PORT}"
echo "----------------------------------------------------------"

# Check if Ollama is running
if curl -s --connect-timeout 2 "${OLLAMA_HOST}/api/tags" > /dev/null 2>&1; then
    echo "[✓] Ollama service detected at ${OLLAMA_HOST}"
    
    # Check if model is downloaded
    if curl -s "${OLLAMA_HOST}/api/tags" | grep -q "${MODEL_NAME%%:*}"; then
        echo "[✓] Model '${MODEL_NAME}' found in Ollama repository."
    else
        echo "[!] Model '${MODEL_NAME}' not found in local Ollama list."
        echo "    To pull it, run:  ollama pull ${MODEL_NAME}"
        echo "    (The web app includes demo sample mode to preview immediately.)"
    fi
else
    echo "[!] Ollama is not running on ${OLLAMA_HOST}"
    echo "    To run live inference:"
    echo "      1. Run 'ollama serve' in a separate terminal"
    echo "      2. Run 'ollama pull ${MODEL_NAME}'"
    echo "    Shoebox will start with setup guidance and bundled demo samples."
fi

echo "----------------------------------------------------------"
echo "Starting FastAPI server on http://localhost:${PORT}..."
echo "Press Ctrl+C to stop."
echo "=========================================================="

python -m uvicorn backend.main:app --host "${HOST}" --port "${PORT}"
