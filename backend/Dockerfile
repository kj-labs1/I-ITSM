# =============================================================================
# I-ITSM Backend — Multi-stage Dockerfile
# =============================================================================
# Stage 1: Build dependencies
# Stage 2: Slim runtime image
# =============================================================================

# ── Stage 1: Builder ────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# System dependencies required by psycopg (libpq) and build tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./

# Install production dependencies into a virtual env so we can copy it later
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .


# ── Stage 2: Runtime ────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Only the minimal runtime library for psycopg
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Copy the pre-built virtual env from the builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application source
COPY . .

# Non-root user for security
RUN addgroup --system iitsm && adduser --system --ingroup iitsm iitsm
USER iitsm

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
