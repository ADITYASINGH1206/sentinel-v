FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY packages/ /app/packages/
COPY services/api/ /app/services/api/

RUN pip install --no-cache-dir \
    -e /app/packages/sv_core \
    -e /app/packages/sv_engine \
    -e /app/packages/sv_fusion \
    -e /app/packages/sv_receipts \
    -e /app/services/api

EXPOSE 8080

CMD ["uvicorn", "sv_api.main:app", "--host", "0.0.0.0", "--port", "8080"]
