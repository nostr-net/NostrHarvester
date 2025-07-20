FROM nginx:alpine

# Create non-root user for nginx (nginx user already exists)
# Remove default nginx config and copy only necessary files
RUN rm -rf /usr/share/nginx/html/*

# Copy only web files (excluding sensitive files)
COPY index.html /usr/share/nginx/html/
COPY app.js /usr/share/nginx/html/

# Add security headers to nginx config
RUN echo 'server { \
    listen 80; \
    server_name _; \
    root /usr/share/nginx/html; \
    index index.html; \
    \
    # Security headers \
    add_header X-Frame-Options "SAMEORIGIN" always; \
    add_header X-Content-Type-Options "nosniff" always; \
    add_header X-XSS-Protection "1; mode=block" always; \
    add_header Referrer-Policy "strict-origin-when-cross-origin" always; \
    \
    location / { \
        try_files $uri $uri/ =404; \
    } \
}' > /etc/nginx/conf.d/default.conf

# Run nginx as non-root user
USER nginx