# Use Python 3.12 slim image as base
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for init.sh
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    unzip \
    git \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy init.sh and make it executable
COPY ../init.sh /tmp/init.sh
RUN chmod +x /tmp/init.sh

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv with system python
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Run init.sh to set up environment (without virtual env creation in container)
RUN /tmp/init.sh || true

# Expose port 5100 for the FastAPI server
EXPOSE 5100

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

# Run the AG-UI server using uv
CMD ["uv", "run", "agui_server.py"]
