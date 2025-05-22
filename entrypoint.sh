#!/bin/sh

set -e

# Wait for PostgreSQL
until pg_isready -h db -p 5432 -U ${POSTGRES_USER}
do
  echo "Waiting for PostgreSQL to start..."
  sleep 2
done

# Run migrations
python manage.py migrate --noinput

# Collect static files
python manage.py collectstatic --noinput

exec "$@"