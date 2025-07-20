FROM nginx:alpine

# Remove default nginx configs
RUN rm -rf /usr/share/nginx/html/* /etc/nginx/conf.d/*

# Copy web files
COPY index.html /usr/share/nginx/html/
COPY app.js /usr/share/nginx/html/
COPY robots.txt /usr/share/nginx/html/
COPY favicon.ico /usr/share/nginx/html/

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Run as non-root user
RUN adduser -D -H -s /sbin/nologin nginx-user && \
    chown -R nginx-user:nginx-user /usr/share/nginx/html /var/cache/nginx /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown nginx-user:nginx-user /var/run/nginx.pid

USER nginx-user