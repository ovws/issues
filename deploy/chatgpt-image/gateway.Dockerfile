FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

RUN python -m pip install --no-cache-dir \
        "fastapi>=0.115,<1" \
        "httpx>=0.28,<1" \
        "python-dotenv>=1.0,<2" \
        "python-multipart>=0.0.20,<1" \
        "uvicorn[standard]>=0.34,<1" \
    && groupadd --system --gid 10001 internal-ai \
    && useradd --system --uid 10001 --gid internal-ai --home-dir /nonexistent internal-ai \
    && mkdir -p /var/lib/internal-ai/media /var/log/internal-ai \
    && chown -R internal-ai:internal-ai /var/lib/internal-ai /var/log/internal-ai

COPY src ./src

USER 10001:10001

EXPOSE 8003

CMD ["python", "-m", "uvicorn", "internal_ai_api.chatgpt_image_app:app", "--host", "0.0.0.0", "--port", "8003", "--no-access-log"]
