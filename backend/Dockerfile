# ==========================================
# Multi-stage Dockerfile para backend (NestJS)
# ==========================================

# Stage 1: Dependencias
FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
COPY prisma ./prisma/
RUN npm ci

# Stage 2: Compilación (Build)
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npx prisma generate
RUN npm run build
# Dejamos las herramientas necesarias para correr prisma y seed en el entrypoint

# Stage 3: Runtime de producción
FROM node:20-alpine AS runner
WORKDIR /app

RUN apk add --no-cache netcat-openbsd

ENV NODE_ENV=production \
    PORT=3000

COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/prisma ./prisma
COPY package*.json tsconfig.json ./
COPY entrypoint.sh ./

RUN chmod +x entrypoint.sh && sed -i 's/\r$//' entrypoint.sh

EXPOSE 3000

ENTRYPOINT ["/bin/sh", "/app/entrypoint.sh"]
