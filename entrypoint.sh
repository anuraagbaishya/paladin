#!/bin/sh
# Wait for Mongo to be ready

MONGO_HOST=${MONGO_HOST:-mongo}
MONGO_PORT=${MONGO_PORT:-27017}

echo "Waiting for Mongo at $MONGO_HOST:$MONGO_PORT..."

echo "Waiting for MongoDB..."
while ! nc -z mongo 27017; do
  sleep 1
done

echo "Mongo is up! Starting Gunicorn..."

exec gunicorn --bind 0.0.0.0:$PORT app:app --workers $WORKERS
