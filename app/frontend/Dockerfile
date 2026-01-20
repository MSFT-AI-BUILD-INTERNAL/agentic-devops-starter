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
# IMPORTANT: Trailing slash is required to match nginx 'location /api/' block
# This ensures frontend calls /api/ which nginx proxies to backend
ARG VITE_AGUI_ENDPOINT=/api/

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
    # Proxy API requests to backend on localhost:5100 (same pod) \
    # IMPORTANT: This must come BEFORE the location / block \
    location /api/ { \
        proxy_pass http://127.0.0.1:5100/; \
        proxy_http_version 1.1; \
        proxy_set_header Upgrade $http_upgrade; \
        proxy_set_header Connection "upgrade"; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; \
        proxy_set_header X-Forwarded-Proto $scheme; \
        proxy_cache_bypass $http_upgrade; \
        proxy_read_timeout 90s; \
        proxy_send_timeout 90s; \
        proxy_buffering off; \
    } \
    \
    # SPA routing - serve index.html for all routes \
    # This must come AFTER /api/ to avoid catching API requests \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
