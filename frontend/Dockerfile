# =============================================================================
# I-ITSM Frontend — Multi-stage Dockerfile
# =============================================================================
# Stage 1: Build static assets with Node 20
# Stage 2: Serve using lightweight Nginx
# =============================================================================

# ── Stage 1: Build ──────────────────────────────────────────────────────────
FROM node:20-alpine AS build

WORKDIR /app

# Leverage cached layers for dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy application source
COPY . .

# Argument to pass API base URL at build time (defaults to localhost:8000)
ARG VITE_API_URL=http://localhost:8000/api/v1
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# ── Stage 2: Runtime ────────────────────────────────────────────────────────
FROM nginx:alpine AS runtime

COPY --from=build /app/dist /usr/share/nginx/html

# Custom Nginx config to support client-side routing and SPA fallback
RUN echo 'server { \
    listen 80; \
    server_name localhost; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html index.htm; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
