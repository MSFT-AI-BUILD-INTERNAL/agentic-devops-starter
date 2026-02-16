# Multi-stage build for React frontend
FROM node:20-alpine AS build

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Set API endpoint to use nginx proxy path (relative URL)
# Frontend will call /api/* which nginx proxies to backend
ARG VITE_AGUI_ENDPOINT=/api

# Build the application with environment variable
# Vite will replace import.meta.env.VITE_AGUI_ENDPOINT at build time
RUN VITE_AGUI_ENDPOINT=$VITE_AGUI_ENDPOINT npm run build

# Production stage with nginx
FROM nginx:alpine

# Copy built assets from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx configuration for SPA routing and API proxy
RUN echo 'server { \
    listen 80; \
    server_name _; \
    root /usr/share/nginx/html; \
    index index.html; \
    \
    # Security headers \
    add_header X-Content-Type-Options "nosniff" always; \
    add_header X-Frame-Options "DENY" always; \
    add_header X-XSS-Protection "1; mode=block" always; \
    add_header Referrer-Policy "strict-origin-when-cross-origin" always; \
    \
    # Block unwanted HTTP methods (WebDAV, etc.) \
    if ($request_method !~ ^(GET|POST|HEAD|OPTIONS)$ ) { \
        return 405; \
    } \
    \
    # API routing is handled by Istio VirtualService (not nginx proxy) \
    # Istio routes /api/* directly to backend:5100 at the ingress layer \
    \
    # SPA routing - serve index.html for all routes \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
