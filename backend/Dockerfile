# ============================================================
# job-agent backend (FastAPI API + pipeline worker share this image)
# ============================================================
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY alembic.ini .
COPY migrations ./migrations
COPY app ./app
COPY scripts ./scripts
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Validation assets (Phase 4A) — present so `docker compose exec api pytest`
# and the OpenAPI export work. requirements-dev is NOT installed by default;
# install it on demand: pip install -r requirements-dev.txt
COPY pytest.ini .
COPY requirements-dev.txt .
COPY tests ./tests

RUN mkdir -p /data/resumes /data/generated

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
