# ---- Base image -----------------------------------------------------------
# Pinned, slim Python 3.12: small, reproducible, and modern — so the
# str | None syntax etc. work fine here even though your local Python is 3.9.
FROM python:3.12-slim

# ---- Environment ----------------------------------------------------------
# PYTHONDONTWRITEBYTECODE: skip .pyc files (smaller, cleaner image).
# PYTHONUNBUFFERED: stream logs straight to stdout so `kubectl logs` is live.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# ---- Dependencies (cached layer) -----------------------------------------
# Copy ONLY requirements first. Docker caches this layer, so rebuilds skip
# re-installing packages as long as requirements.txt is unchanged.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Application code -----------------------------------------------------
COPY app/ ./app/

# ---- Run as non-root (security best practice) -----------------------------
RUN useradd --create-home --uid 1000 appuser
USER appuser

EXPOSE 8000

# ---- Container-level health check ----------------------------------------
# Reuses the /health endpoint we built. `docker ps` will show "healthy".
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"

# ---- Start the server -----------------------------------------------------
# Bind to 0.0.0.0 (not 127.0.0.1) so it's reachable from outside the container.
# Honor the PORT env var so Helm/Kubernetes can override it later.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]