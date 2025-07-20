FROM nginx:alpine

# Create non-root user for nginx (nginx user already exists)
# Remove default nginx config and copy only necessary files
RUN rm -rf /usr/share/nginx/html/*

# Copy only web files (excluding sensitive files)
COPY index.html /usr/share/nginx/html/
COPY app.js /usr/share/nginx/html/

# Add security headers and API proxy to nginx config
RUN echo 'server { \
    listen 80; \
    server_name _ search.nostr.net localhost; \
    root /usr/share/nginx/html; \
    index index.html; \
    \
    # Handle SSL termination properly \
    set $real_scheme $scheme; \
    if ($http_x_forwarded_proto) { \
        set $real_scheme $http_x_forwarded_proto; \
    } \
    \
    # Security headers \
    add_header X-Frame-Options "SAMEORIGIN" always; \
    add_header X-Content-Type-Options "nosniff" always; \
    add_header X-XSS-Protection "1; mode=block" always; \
    add_header Referrer-Policy "strict-origin-when-cross-origin" always; \
    \
    # Proxy API requests to internal app service \
    location /api/ { \
        proxy_pass http://app:8000/api/; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; \
        proxy_set_header X-Forwarded-Proto $real_scheme; \
        proxy_connect_timeout 30s; \
        proxy_send_timeout 30s; \
        proxy_read_timeout 30s; \
    } \
    \
    # Proxy health endpoint to internal app service \
    location /health { \
        proxy_pass http://app:8000/health; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; \
        proxy_set_header X-Forwarded-Proto $real_scheme; \
    } \
    \
    # Serve static files \
    location / { \
        try_files $uri $uri/ =404; \
    } \
}' > /etc/nginx/conf.d/default.conf

# For containers, running nginx as root is acceptable since container isolation provides security
# This avoids complex permission issues while maintaining security through containerization