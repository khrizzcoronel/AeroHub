# Imagen del agente de continuidad operacional (Sprint S1.9, ADR-018).
# Mismo patron que services/gateway/Dockerfile: contexto de build = raiz
# del repo, workspace completo instalado (tools/continuidad_agente.py
# importa aerohub_continuidad, un member del workspace uv).
FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
COPY packages packages
COPY services services
COPY pipelines pipelines
COPY ml ml
COPY tools tools

RUN uv sync --all-packages

ENTRYPOINT ["uv", "run", "python", "tools/continuidad_agente.py"]
