ARG BUILDPLATFORM
ARG TARGETPLATFORM

FROM --platform=$BUILDPLATFORM node:22-alpine AS web-build

WORKDIR /app/web
COPY upstream/chatgpt2api/web/package.json upstream/chatgpt2api/web/bun.lock ./
RUN npm install

COPY upstream/chatgpt2api/VERSION /app/VERSION
COPY upstream/chatgpt2api/CHANGELOG.md /app/CHANGELOG.md
COPY upstream/chatgpt2api/web ./
RUN NEXT_PUBLIC_APP_VERSION="$(cat /app/VERSION)" npm run build


FROM --platform=$TARGETPLATFORM python:3.13-slim AS app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        git \
        libpq-dev \
        openssl \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir uv

COPY upstream/chatgpt2api/pyproject.toml upstream/chatgpt2api/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY upstream/chatgpt2api/main.py ./
COPY upstream/chatgpt2api/config.json ./
COPY upstream/chatgpt2api/VERSION ./
COPY upstream/chatgpt2api/api ./api
COPY upstream/chatgpt2api/services ./services
COPY upstream/chatgpt2api/utils ./utils
COPY upstream/chatgpt2api/scripts ./scripts
COPY --from=web-build /app/web/out ./web_dist

RUN groupadd --system --gid 10002 chatgpt2api \
    && useradd --system --uid 10002 --gid chatgpt2api --home-dir /nonexistent chatgpt2api \
    && mkdir -p /app/data \
    && chown -R chatgpt2api:chatgpt2api /app

USER 10002:10002

EXPOSE 80

CMD ["/app/.venv/bin/python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80", "--no-access-log"]
