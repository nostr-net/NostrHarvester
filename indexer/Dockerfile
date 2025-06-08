FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY indexer/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Start the indexer
CMD ["python", "-m", "indexer.nostr_indexer"]