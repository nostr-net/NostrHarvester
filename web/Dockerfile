FROM nginx:alpine

# Remove ALL default nginx configs to prevent conflicts
RUN rm -rf /usr/share/nginx/html/* /etc/nginx/conf.d/* /etc/nginx/sites-enabled/* /etc/nginx/sites-available/*

# Copy only web files
COPY index.html /usr/share/nginx/html/
COPY app.js /usr/share/nginx/html/

# Create completely clean nginx config with NO redirects
RUN echo 'events { worker_connections 1024; } \
http { \
    include /etc/nginx/mime.types; \
    default_type application/octet-stream; \
    sendfile on; \
    keepalive_timeout 65; \
    \
    map $http_x_forwarded_proto $proxy_x_forwarded_proto { \
        default $http_x_forwarded_proto; \
        '"'"''"'"' $scheme; \
    } \
    \
    server { \
        listen 80 default_server; \
        server_name _; \
        root /usr/share/nginx/html; \
        index index.html; \
        \
        # Security headers \
        add_header X-Frame-Options "SAMEORIGIN" always; \
        add_header X-Content-Type-Options "nosniff" always; \
        add_header X-XSS-Protection "1; mode=block" always; \
        \
        # Proxy API requests \
        location /api/ { \
            proxy_pass http://app:8000/api/; \
            proxy_set_header Host $http_host; \
            proxy_set_header X-Real-IP $remote_addr; \
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; \
            proxy_set_header X-Forwarded-Proto $proxy_x_forwarded_proto; \
            proxy_set_header X-Forwarded-Host $http_host; \
            proxy_redirect off; \
            proxy_buffering off; \
            proxy_request_buffering off; \
            proxy_http_version 1.1; \
            proxy_set_header Connection ""; \
        } \
        \
        # Proxy health endpoint \
        location /health { \
            proxy_pass http://app:8000/health; \
            proxy_set_header Host $http_host; \
            proxy_set_header X-Real-IP $remote_addr; \
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; \
            proxy_set_header X-Forwarded-Proto $proxy_x_forwarded_proto; \
            proxy_set_header X-Forwarded-Host $http_host; \
            proxy_redirect off; \
        } \
        \
        # Proxy metrics endpoint \
        location /metrics { \
            proxy_pass http://app:8000/metrics; \
            proxy_set_header Host $http_host; \
            proxy_set_header X-Real-IP $remote_addr; \
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; \
            proxy_set_header X-Forwarded-Proto $proxy_x_forwarded_proto; \
            proxy_set_header X-Forwarded-Host $http_host; \
            proxy_redirect off; \
        } \
        \
        # Proxy favicon and robots.txt \
        location /favicon.ico { \
            proxy_pass http://app:8000/favicon.ico; \
            proxy_set_header Host $http_host; \
            proxy_set_header X-Real-IP $remote_addr; \
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; \
            proxy_set_header X-Forwarded-Proto $proxy_x_forwarded_proto; \
            proxy_set_header X-Forwarded-Host $http_host; \
            proxy_redirect off; \
        } \
        \
        location /robots.txt { \
            proxy_pass http://app:8000/robots.txt; \
            proxy_set_header Host $http_host; \
            proxy_set_header X-Real-IP $remote_addr; \
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; \
            proxy_set_header X-Forwarded-Proto $proxy_x_forwarded_proto; \
            proxy_set_header X-Forwarded-Host $http_host; \
            proxy_redirect off; \
        } \
        \
        # Serve static files \
        location / { \
            try_files $uri $uri/ =404; \
        } \
    } \
}' > /etc/nginx/nginx.conf

# For containers, running nginx as root is acceptable since container isolation provides security
# This avoids complex permission issues while maintaining security through containerization