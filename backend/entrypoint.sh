#!/bin/sh
set -e

echo "==> Esperando a que PostgreSQL este listo..."
until nc -z -v -w30 bd-perfumes 5432 2>/dev/null; do
  echo "Esperando puerto 5432..."
  sleep 2
done

echo "==> Aplicando esquema de base de datos..."
npx prisma db push --skip-generate

echo "==> Ejecutando Seed automático de inicio..."
npm run prisma:seed || true

echo "==> Iniciando servidor NestJS..."
exec node dist/main
