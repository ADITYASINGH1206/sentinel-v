FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential ffmpeg && \
    rm -rf /var/lib/apt/lists/*

COPY packages/ /app/packages/
COPY services/workers/ /app/services/workers/

RUN pip install --no-cache-dir \
    -e /app/packages/sv_core \
    -e /app/packages/sv_engine \
    -e /app/packages/sv_fusion \
    -e /app/packages/sv_receipts \
    -e /app/services/workers

# Non-root user execution for sandboxed worker processing (SPEC §12)
RUN groupadd -g 1000 svuser && \
    useradd -u 1000 -g svuser -m -s /bin/bash svuser && \
    chown -R svuser:svuser /app

USER svuser

CMD ["celery", "-A", "sv_workers.celery_app", "worker", "--loglevel=INFO", "-Q", "ingest,preprocess,finalize,anchor,monitor"]
