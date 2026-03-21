#!/bin/bash

until curl -s http://127.0.0.1:11434/api/tags > /dev/null 2>&1; do
    echo "Waiting for Ollama..."
    sleep 2
done

if ! ollama list 2>/dev/null | grep -q "qwen2.5"; then
    echo "Pulling qwen2.5:latest..."
    ollama pull qwen2.5:latest
fi

echo "Ollama ready"