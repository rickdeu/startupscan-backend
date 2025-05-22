#!/bin/sh

set -e

# Wait for PostgreSQL
until pg_isready -h db -p 5432 -U ${POSTGRES_USER}
do
  echo "Waiting for PostgreSQL to start..."
  sleep 2
done

# Wait for Redis
until nc -z redis 6379
do
  echo "Waiting for Redis to start..."
  sleep 2
done

exec celery -A startupscan $@