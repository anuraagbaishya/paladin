#!/bin/sh

MONGO_HOST=${MONGO_HOST:-mongo}
MONGO_PORT=${MONGO_PORT:-27017}

# Skip the health check for connection strings (remote/Atlas instances)
case "$MONGO_HOST" in
  *"://"*)
    echo "Remote Mongo URI detected, skipping health check..."
    ;;
  *)
    echo "Waiting for Mongo at $MONGO_HOST:$MONGO_PORT..."
    while ! nc -z "$MONGO_HOST" "$MONGO_PORT"; do
      sleep 1
    done
    echo "Mongo is up!"
    ;;
esac

echo "Starting Gunicorn..."

exec gunicorn --bind 0.0.0.0:$PORT app:app --workers $WORKERS
