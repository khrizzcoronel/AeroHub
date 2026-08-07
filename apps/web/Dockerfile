# Imagen de desarrollo de apps/web. Contexto de build = raiz del repo (ver
# infra/docker-compose.yml, "context: .."): es un monorepo Nx, necesita el
# package.json/nx.json raiz, no solo la carpeta de la app.
FROM node:22-slim

WORKDIR /app

COPY package.json package-lock.json nx.json tsconfig.json ./
# npm install, no npm ci: el lockfile del repo se genero con un npm mas
# nuevo que el de esta imagen (node:22-slim) -- `npm ci` rechaza esa
# discrepancia de version aunque `npm install` en el host confirme que el
# lockfile SI esta al dia (hallazgo empirico). Imagen de desarrollo, no
# build reproducible de produccion -- misma logica que "uv sync" sin
# --frozen en services/gateway/Dockerfile.
RUN npm install

COPY apps apps

EXPOSE 4200

ENV NX_DAEMON=false

# --host 0.0.0.0: el dev-server de Angular (Vite) escucha en localhost por
# defecto, invisible fuera del contenedor sin esto.
#
# Hallazgo empirico (2026-08-05): sin volumen, /app/.nx/workspace-data/
# vive en la capa escribible del CONTENEDOR (no de la imagen) -- un
# `docker stop` no siempre le da tiempo a Nx de soltar
# project-graph.lock/machine-v3.lock antes del SIGKILL. Si despues el
# mismo contenedor se reinicia con `docker start`/`docker compose up -d`
# (sin --force-recreate ni --build, que si generan un contenedor nuevo
# limpio), esos locks quedan huerfanos y `nx serve` se cuelga para
# siempre en "Waiting for web:serve:development in another nx process".
# Se limpia el cache de Nx en cada arranque -- se regenera solo, no hay
# nada que valga la pena preservar entre arranques en un contenedor de
# desarrollo sin volumen.
CMD ["sh", "-c", "rm -rf /app/.nx/workspace-data && npx nx serve web --host 0.0.0.0 --port 4200"]
