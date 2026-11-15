@echo off
title AETHER — Pull Optimised Model Ensemble
echo ============================================================
echo  AETHER Model Ensemble Pull Script
echo  Optimised for Snapdragon X (16GB, ARM64 CPU-only)
echo ============================================================
echo.

echo [1/4] Pulling qwen2.5:3b (chat brain - 75%% smaller KV cache)...
ollama pull qwen2.5:3b
if errorlevel 1 echo WARNING: qwen2.5:3b failed to pull. AETHER will fall back to llama3.2:3b.
echo.

echo [2/4] Pulling qwen2-vl:2b (vision model - dynamic resolution OCR)...
ollama pull qwen2-vl:2b
if errorlevel 1 echo WARNING: qwen2-vl:2b failed. AETHER will fall back to moondream.
echo.

echo [3/4] Pulling qwen2.5-coder:3b (code specialist)...
ollama pull qwen2.5-coder:3b
if errorlevel 1 echo WARNING: qwen2.5-coder:3b failed. Code tasks will use the main brain model.
echo.

echo [4/4] Pulling nomic-embed-text (embedding model for semantic search)...
ollama pull nomic-embed-text
if errorlevel 1 echo WARNING: nomic-embed-text failed. Semantic search will not be available.
echo.

echo ============================================================
echo  All models pulled. Verify with: ollama list
echo ============================================================
ollama list
echo.
pause
