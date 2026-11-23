# ==========================================
# Multi-stage Dockerfile para frontend (React + Vite + Nginx)
# ==========================================

# Stage 1: Build de la app
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# Argumento para URL del backend en tiempo de build
ARG VITE_API_URL=http://localhost:3000
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# Stage 2: Servidor Web Nginx ultra-ligero
FROM nginx:alpine AS runner

COPY --from=builder /app/dist /usr/share/nginx/html

# Configuración Nginx para soporte de React Router (SPA)
RUN printf 'server {\n\
    listen 80;\n\
    server_name localhost;\n\
    location / {\n\
        root /usr/share/nginx/html;\n\
        index index.html index.htm;\n\
        try_files $uri $uri/ /index.html;\n\
    }\n\
}\n' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
