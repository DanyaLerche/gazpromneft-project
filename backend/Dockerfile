FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend /app/backend
COPY config.py /app/config.py
COPY .env /app/.env
COPY alembic.ini /app/alembic.ini

EXPOSE 8000

CMD alembic upgrade head && uvicorn backend.main:app --host 0.0.0.0 --port 8000
