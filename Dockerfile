# Multi-stage build with Python 3.12
FROM python:3.12-slim AS builder
WORKDIR /app

# Install system dependencies and Poetry in one layer
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && pip install --no-cache-dir poetry \
    && apt-get clean && rm -rf /var/lib/apt/lists/* ~/.cache/pypoetry

# Copy only dependency files
COPY pyproject.toml poetry.lock ./

# Install only main dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-root

# Final stage with Python 3.12
FROM python:3.12-slim
WORKDIR /app

# Install minimal runtime dependencies (remove curl if not needed)
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy only necessary dependencies from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn
# Only copy uvicorn (adjust if other binaries are needed)

# Copy minimal source code
COPY data/* ./
COPY static/* ./
COPY *.py ./
# Copy only the required file(s)

# Create non-root user
RUN useradd -m -r appuser && mkdir -p /app && chown appuser:appuser /app && \
    mkdir -p /app/temp-data && chown appuser:appuser /app/temp-data
USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Expose the port FastAPI will run on
EXPOSE 8090

# Command to run the FastAPI app with uvicorn
CMD ["uvicorn", "main_app:app", "--host", "0.0.0.0", "--port", "8090"]