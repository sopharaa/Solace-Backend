# ─────────────────────────────────────────────
# Stage 1: Build / dependency layer
# ─────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages into a dedicated prefix
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ─────────────────────────────────────────────
# Stage 2: Production runtime
# ─────────────────────────────────────────────
FROM python:3.12-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Runtime-only system deps (libpq for psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy project source
COPY . .

# Create a non-root user for security
RUN addgroup --system --gid 1001 django && \
    adduser  --system --uid 1001 --ingroup django appuser && \
    chown -R appuser:django /app

USER appuser

EXPOSE 8080

# Run database migrations then start Gunicorn
# Cloud Run sets PORT=8080; fall back to 8000 for local runs
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn solace_backend.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3 --timeout 120"]
