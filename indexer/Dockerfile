FROM python:3.11-slim

# Create non-root user
RUN groupadd -r indexer && useradd -r -g indexer indexer

WORKDIR /app

# Install dependencies
COPY indexer/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy only necessary application code
COPY indexer/ ./indexer/
COPY common/ ./common/
COPY migrations/ ./migrations/

# Change ownership to non-root user
RUN chown -R indexer:indexer /app

# Switch to non-root user
USER indexer

# Start the indexer
CMD ["python", "-m", "indexer.nostr_indexer"]