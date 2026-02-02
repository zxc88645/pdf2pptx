# syntax=docker/dockerfile:1
# Enable BuildKit for cache: DOCKER_BUILDKIT=1 or podman build
# Stage 1: build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci 2>/dev/null || npm install
COPY . .
RUN npm run build

# Stage 2: serve with nginx (read-only root filesystem in compose)
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
