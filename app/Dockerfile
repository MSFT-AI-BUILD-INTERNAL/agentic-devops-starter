# Use Python 3.12 slim image as base
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv with system python
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Expose port 5100 for the FastAPI server
EXPOSE 5100

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

# Run the AG-UI server
CMD ["python", "agui_server.py"]
