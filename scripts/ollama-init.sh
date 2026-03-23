#!/bin/bash
set -e

echo "Waiting for Ollama API..."
until curl -s http://0.0.0.0:11434/api/tags > /dev/null 2>&1; do
    sleep 2
done

echo "Checking for qwen2.5..."
if ! ollama list 2>/dev/null | grep -q "qwen2.5"; then
    echo "Pulling qwen2.5:latest..."
    ollama pull qwen2.5:latest
fi

echo "Ollama ready with qwen2.5"