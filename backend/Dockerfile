# EMASDEP Backend - Single stage build
FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/src/ src/
COPY backend/pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY skills/ skills/

ENV PYTHONUNBUFFERED=1
ENV EMASDEP_ENV=production

EXPOSE 8000

CMD ["emasdep", "serve", "--host", "0.0.0.0", "--port", "8000"]
