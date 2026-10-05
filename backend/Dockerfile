FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
# Migracje + dane testowe (gdy baza pusta) wykonuje lifespan aplikacji (AUTO_CREATE_TABLES / SEED_ON_STARTUP).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
