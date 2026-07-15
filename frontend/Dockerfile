# ---- deps ----
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json ./
RUN npm install

# ---- build ----
FROM node:20-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Baked into the Next rewrite so /api/* proxies to the backend service at runtime.
ARG BACKEND_URL=http://backend:8000
ENV BACKEND_URL=$BACKEND_URL
RUN npm run build

# ---- run (standalone) ----
FROM node:20-alpine AS run
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/public ./public
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
ENV HOSTNAME=0.0.0.0
EXPOSE 3000
# Force bind to 0.0.0.0. Render injects HOSTNAME=<pod-hostname> at runtime, which Next.js standalone
# would otherwise bind to (unreachable by Render's router -> 502). The sh -c prefix overrides it at exec.
CMD ["sh", "-c", "HOSTNAME=0.0.0.0 node server.js"]
