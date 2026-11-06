# ==============================================================================
# CareerPilot AI — Frontend Multi-Stage Containerfile (Node 22 + Nginx Alpine)
# ==============================================================================

# Stage 1: Build production assets with Node.js
FROM node:22-alpine as builder

WORKDIR /app

# Install dependencies with frozen lockfile
COPY package*.json ./
RUN npm ci

# Copy source code and build Vite bundle
COPY . .
RUN npm run build

# Stage 2: Serve optimized static assets with Nginx Alpine
FROM nginx:alpine

# Copy built artifacts from Stage 1
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
