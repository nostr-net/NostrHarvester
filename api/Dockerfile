FROM python:3.11-slim

# Create non-root user
RUN groupadd -r apiuser && useradd -r -g apiuser apiuser

WORKDIR /app

# Install dependencies
COPY api/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy only necessary application code
COPY api/ ./api/
COPY common/ ./common/
COPY migrations/ ./migrations/
COPY migrate.py ./
COPY web/ ./web/

# Change ownership to non-root user
RUN chown -R apiuser:apiuser /app

# Switch to non-root user
USER apiuser

# Start the API with proxy headers support for SSL termination
CMD ["uvicorn", "api.api_fastapi:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]

EXPOSE 8000
