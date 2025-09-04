# Production-optimized Docker image for Stellar SDEX Connector v3.0
FROM python:3.11-slim as builder

# Security hardening
RUN groupadd -r stellar && useradd -r -g stellar stellar

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

# Copy user and install runtime dependencies
COPY --from=builder /etc/passwd /etc/passwd
COPY --from=builder /etc/group /etc/group

# Copy application
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY . .

USER stellar

EXPOSE 8000

CMD ["python", "-m", "hummingbot.connector.exchange.stellar"]