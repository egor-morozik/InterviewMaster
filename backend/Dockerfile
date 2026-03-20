FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
ENV UV_PROJECT_ENVIRONMENT=/usr/local
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache
COPY app/ ./app/
CMD ["uv", "run", "python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
