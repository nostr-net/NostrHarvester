FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY api/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Start the API
CMD ["uvicorn", "api.api_fastapi:app", "--host", "0.0.0.0", "--port", "8000"]

EXPOSE 8000
