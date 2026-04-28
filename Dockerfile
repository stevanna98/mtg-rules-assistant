# Stage 1: builder — install dependencies
FROM python:3.12-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy only dependency files first (caching trick)
COPY pyproject.toml uv.lock ./

# Install dependencies into a virtual environment
RUN uv sync --frozen --no-dev

# Stage 2: runtime — slim final image
FROM python:3.12-slim AS runtime

# Create a non-root user (security best practice)
RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

# Copy the virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy your application code
COPY src/ ./src/

# Use the venv's python
ENV PATH="/app/.venv/bin:$PATH"

USER app

EXPOSE 8000

CMD ["uvicorn", "src.mtg_rules.api:app", "--host", "0.0.0.0", "--port", "8000"]