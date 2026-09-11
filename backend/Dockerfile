# Build context is the repository root (not this backend/ directory) so the
# image can bake in ../frontend too — app.main serves it via StaticFiles.
# docker-compose.yml and render.yaml both build with context: .. / dockerContext: .

FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY frontend/ /frontend

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
