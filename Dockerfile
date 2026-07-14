# SubTrack backend image (api / worker / beat via CMD arg)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY build/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY code/backend/ ./

# Default command (overridden per-service by docker-compose):
#   api    -> uvicorn app.main:app --host 0.0.0.0 --port 8000
#   worker -> celery -A app.tasks.celery_app worker --loglevel=info
#   beat   -> celery -A app.tasks.celery_app beat --loglevel=info
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
