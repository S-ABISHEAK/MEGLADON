FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libgl1 libegl1 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend
COPY backend/requirements.txt backend/requirements-postgres.txt ./
RUN pip install --no-cache-dir -r requirements-postgres.txt

COPY backend/ .
COPY models/ /app/models/

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "app.workers.worker"]
