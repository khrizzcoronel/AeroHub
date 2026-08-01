# Imagen de desarrollo de apps/fids-player. Ver el comentario equivalente
# en apps/web/Dockerfile.
FROM node:22-slim

WORKDIR /app

COPY package.json package-lock.json nx.json tsconfig.json ./
# npm install, no npm ci -- ver el comentario equivalente en apps/web/Dockerfile.
RUN npm install

COPY apps apps

EXPOSE 4300

CMD ["npx", "nx", "serve", "fids-player", "--host", "0.0.0.0", "--port", "4300"]
