FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SETUPTOOLS_SCM_PRETEND_VERSION_FOR_GEMINI_WEBAPI=0.0+internal

WORKDIR /app

COPY upstream/gemini-api ./upstream/gemini-api
COPY pyproject.toml ./pyproject.toml
COPY README.md ./README.md
COPY src ./src

RUN python -m pip install --no-cache-dir ./upstream/gemini-api . \
    && groupadd --system --gid 10001 internal-ai \
    && useradd --system --uid 10001 --gid internal-ai --home-dir /nonexistent internal-ai \
    && mkdir -p /var/lib/internal-ai/media /var/log/internal-ai \
    && chown -R internal-ai:internal-ai /var/lib/internal-ai /var/log/internal-ai

USER 10001:10001

EXPOSE 8002

CMD ["python", "-m", "uvicorn", "internal_ai_api.gemini_app:app", "--host", "0.0.0.0", "--port", "8002", "--no-access-log"]
