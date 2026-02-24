#!/bin/bash
set -e

echo "=== Iniciando Celery Worker ==="
celery -A app.workers.celery_app worker --loglevel=info --concurrency=2 &
CELERY_PID=$!

echo "=== Iniciando Uvicorn ==="
uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips "*" &
UVICORN_PID=$!

# Se qualquer processo morrer, mata o outro e sai
trap "kill $CELERY_PID $UVICORN_PID 2>/dev/null; exit 1" SIGTERM SIGINT

wait -n $CELERY_PID $UVICORN_PID
echo "=== Um dos processos morreu, encerrando ==="
kill $CELERY_PID $UVICORN_PID 2>/dev/null
exit 1
