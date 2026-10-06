# Estagio 1: gera os arquivos estaticos. Node e node_modules ficam aqui.
FROM node:24-alpine AS build
WORKDIR /app
# So o package.json e o lock primeiro: se as dependencias nao mudaram, o
# Docker reaproveita esta camada e o build pula o npm ci inteiro.
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Estagio 2: so o nginx e os arquivos prontos. Imagem de ~25 MB, sem Node.
# A variante unprivileged roda o nginx sem root.
FROM nginxinc/nginx-unprivileged:1.30-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/out /usr/share/nginx/html
EXPOSE 8080
