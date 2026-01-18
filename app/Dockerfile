# Use Python 3.12 slim image as base
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# - curl: HTTP client for health checks and API calls
# - gcc, g++: C/C++ compilers for building Python packages with native extensions
# - libffi-dev: Required by azure-identity and cryptography
# - libssl-dev: SSL/TLS support for HTTPS connections
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY app/pyproject.toml app/uv.lock ./

# Install dependencies using uv with system python
RUN uv sync --frozen --no-dev

# Copy application code
COPY app/ .

# Expose port 5100 for the FastAPI server
EXPOSE 5100

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

# Run the AG-UI server using uv
CMD ["uv", "run", "agui_server.py"]
