# Use Python 3.11 to match your development environment
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy poetry configuration files
COPY pyproject.toml poetry.lock ./

# Configure poetry: Don't create virtual env, install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Copy application code
COPY app/ ./app/
COPY prisma/ ./prisma/
COPY docker-entrypoint.sh ./

# Copy environment file (for Docker builds)
COPY .env ./

# Make entrypoint script executable
RUN chmod +x docker-entrypoint.sh

# Generate Prisma client
RUN poetry run prisma generate

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Use entrypoint script
ENTRYPOINT ["./docker-entrypoint.sh"]
