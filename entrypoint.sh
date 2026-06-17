#!/bin/sh

echo "Waiting for postgres..."
while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
  sleep 0.1
done
echo "PostgreSQL started"

echo "Running migrations..."
alembic upgrade head

echo "Starting server..."
if [ "${DEBUGPY:-0}" = "1" ]; then
  DEBUGPY_HOST="${DEBUGPY_HOST:-0.0.0.0}"
  DEBUGPY_PORT="${DEBUGPY_PORT:-5678}"
  DEBUGPY_WAIT_FOR_CLIENT="${DEBUGPY_WAIT_FOR_CLIENT:-1}"
  DEBUGPY_RELOAD="${DEBUGPY_RELOAD:-1}"
  DEBUGPY_SUBPROCESS="${DEBUGPY_SUBPROCESS:-1}"

  WAIT_FLAG=""
  if [ "$DEBUGPY_WAIT_FOR_CLIENT" = "1" ]; then
    WAIT_FLAG="--wait-for-client"
  fi

  SUBPROCESS_FLAG=""
  if [ "$DEBUGPY_SUBPROCESS" = "1" ]; then
    SUBPROCESS_FLAG="--configure-subProcess True"
  fi

  if [ "$DEBUGPY_RELOAD" = "1" ]; then
    exec python -m debugpy --listen "${DEBUGPY_HOST}:${DEBUGPY_PORT}" $WAIT_FLAG $SUBPROCESS_FLAG -m uvicorn app.asgi:application --host 0.0.0.0 --port 8000 --reload
  fi

  exec python -m debugpy --listen "${DEBUGPY_HOST}:${DEBUGPY_PORT}" $WAIT_FLAG $SUBPROCESS_FLAG -m gunicorn app.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --workers 1
fi

exec "$@"
