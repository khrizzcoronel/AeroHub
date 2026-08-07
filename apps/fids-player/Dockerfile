# Imagen de desarrollo de apps/fids-player. Ver el comentario equivalente
# en apps/web/Dockerfile.
FROM node:22-slim

WORKDIR /app

COPY package.json package-lock.json nx.json tsconfig.json ./
# npm install, no npm ci -- ver el comentario equivalente en apps/web/Dockerfile.
RUN npm install

COPY apps apps

EXPOSE 4300

# Hallazgo empirico -- ver el comentario equivalente en apps/web/Dockerfile:
# sin esto, un contenedor reiniciado (no recreado) puede quedar con locks
# huerfanos de Nx y `nx serve` se cuelga para siempre.
CMD ["sh", "-c", "rm -rf /app/.nx/workspace-data && npx nx serve fids-player --host 0.0.0.0 --port 4300"]
