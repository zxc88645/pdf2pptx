# Frontend: Vue 3 + Vite, Node 24
FROM node:24-slim

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
EXPOSE 5173

# Vite dev server: listen on 0.0.0.0 for Docker, proxy target set via env in compose
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
