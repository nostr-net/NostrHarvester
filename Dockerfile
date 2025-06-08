FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Default command
CMD ["uvicorn", "api_fastapi:app", "--host", "0.0.0.0", "--port", "8000"]

EXPOSE 8000
