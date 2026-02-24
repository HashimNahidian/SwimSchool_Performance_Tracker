#!/usr/bin/env sh
set -eu

alembic upgrade head
exec gunicorn main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 --workers 2 --timeout 120
