# Imagen de desarrollo del gateway. Contexto de build = raiz del repo (ver
# infra/docker-compose.yml, "context: .."): services/gateway/main.py
# compone routers de VARIOS paquetes del workspace uv (aerohub_aodb,
# aerohub_fids, aerohub_gates, aerohub_ramp, aerohub_tenancy), no solo
# aerohub_gateway -- necesita el workspace completo instalado, igual que
# en el host (uv sync en la raiz), no un `pip install` aislado de un solo
# paquete.
FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
COPY packages packages
COPY services services
COPY pipelines pipelines
COPY ml ml

# --all-packages: el proyecto RAIZ declara `dependencies = []` (solo trae
# el grupo `dev` de herramientas) -- sin esta bandera, `uv sync` no instala
# fastapi/uvicorn/sqlalchemy/etc. de NINGUN member del workspace (hallazgo
# empirico: la primera imagen construida sin ella arranco sin `uvicorn`
# instalado). Sin --frozen: uv.lock del repo puede quedar temporalmente
# desactualizado frente a un pyproject.toml de un member recien editado
# (el binario `uv` no esta disponible en el host de desarrollo de este
# proyecto, ver docs/runbooks -- aqui, dentro de la imagen, SI lo esta,
# asi que se resuelve y regenera el lock en el momento del build).
RUN uv sync --all-packages

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--app-dir", "services/gateway", "--host", "0.0.0.0", "--port", "8000"]
