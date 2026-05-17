FROM python:3.11-slim

WORKDIR /app

# Build deps for kerykeion's swisseph extension
RUN apt-get update && apt-get install -y --no-install-recommends \
      gcc g++ make python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir -e .

COPY PERSONA.md REFERENCE.md schema.sql manifest.yaml ./
COPY data/ ./data/

ENV PYTHONUNBUFFERED=1 \
    ORA_DB_PATH=/data/ora.db

VOLUME ["/data"]

CMD ["python", "-m", "ora.app"]
