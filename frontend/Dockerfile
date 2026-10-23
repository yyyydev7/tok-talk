FROM node:24.22.1-alpine3.24 AS dependencies
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM dependencies AS development
COPY . .
EXPOSE 5174
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

FROM dependencies AS build
ARG VITE_AUTH_BASE_URL=""
ARG VITE_RAG_BASE_URL=""
ENV VITE_AUTH_BASE_URL=${VITE_AUTH_BASE_URL}
ENV VITE_RAG_BASE_URL=${VITE_RAG_BASE_URL}
COPY . .
RUN npm run build

FROM nginx:1.30.6-alpine3.24 AS release
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=6 \
    CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
