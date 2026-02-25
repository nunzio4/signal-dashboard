# ── Stage 1: Build React frontend ──
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python backend + serve built frontend ──
FROM python:3.12-slim
WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./

# Copy built frontend into backend/static
COPY --from=frontend-build /app/frontend/dist ./static

# Railway sets PORT env var
ENV PORT=8000

EXPOSE 8000

# At runtime: the Railway volume is mounted at /app/data.
# If no database exists yet (first deploy or volume wipe), copy the
# seed database so the app starts with historical data.
CMD ["sh", "-c", "\
  mkdir -p /app/data && \
  if [ ! -f /app/data/signals.db ]; then \
    echo 'No database found on volume — seeding from seed.db'; \
    cp /app/seed.db /app/data/signals.db; \
  else \
    echo 'Existing database found on volume — preserving data'; \
  fi && \
  uvicorn app.main:app --host 0.0.0.0 --port $PORT"]
