from sv_workers.celery_app import celery_app


@celery_app.task(name="sv_workers.tasks.ingest.run_ingest")
def run_ingest(analysis_id: str, media_url: str):
    """Task: Download, hash, sniff container, inspect C2PA manifest, and deduplicate."""
    return {"analysis_id": analysis_id, "status": "ingested"}
