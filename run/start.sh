#!/usr/bin/env bash
# Start the full SubTrack stack (native, no Docker).
# Requires: Postgres + Valkey already running (see plan/01_requirements.md).
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/code/backend"
VENV="$ROOT/.venv"
export SUBTRACK_CREDENTIALS_PATH="$ROOT/credentials.yaml"
export PYTHONPATH="$BACKEND"

echo "==> MailHog (local SMTP + UI)"
if ! pgrep -f /usr/local/bin/mailhog >/dev/null; then
  setsid /usr/local/bin/mailhog -smtp-bind-addr 127.0.0.1:1025 -ui-bind-addr 127.0.0.1:8025 >/tmp/mailhog.log 2>&1 &
fi

echo "==> Alembic migrations"
( cd "$BACKEND" && source "$VENV/bin/activate" && alembic upgrade head )

echo "==> FastAPI (uvicorn :8000)"
( cd "$BACKEND" && source "$VENV/bin/activate" && setsid uvicorn app.main:app --host 0.0.0.0 --port 8000 >/tmp/subtrack_api.log 2>&1 & )

echo "==> Celery worker"
( cd "$BACKEND" && source "$VENV/bin/activate" && setsid celery -A app.tasks.celery_app worker --loglevel=info >/tmp/subtrack_worker.log 2>&1 & )

echo "==> Celery beat (daily alert sweep)"
( cd "$BACKEND" && source "$VENV/bin/activate" && setsid celery -A app.tasks.celery_app beat --loglevel=info >/tmp/subtrack_beat.log 2>&1 & )

echo "==> Frontend dev server (:5173)"
( cd "$ROOT/code/frontend" && setsid npm run dev >/tmp/subtrack_fe.log 2>&1 & )

sleep 3
echo "Done."
echo "  API docs : http://localhost:8000/docs"
echo "  UI        : http://localhost:5173"
echo "  MailHog   : http://localhost:8025"
