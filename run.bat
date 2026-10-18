@echo off
REM Shoebox - Local Receipt Scanner & Organizer for Windows
SET PORT=8000
SET MODEL_NAME=gemma3:4b
SET OLLAMA_HOST=http://localhost:11434

echo ==========================================================
echo   SHOEBOX: 100%% LOCAL RECEIPT PHOTO TO CLEAN SPREADSHEET
echo ==========================================================
echo Model configured : %MODEL_NAME%
echo Ollama Endpoint  : %OLLAMA_HOST%
echo Web UI URL       : http://localhost:%PORT%
echo ----------------------------------------------------------

python -m uvicorn backend.main:app --host 0.0.0.0 --port %PORT%
