import logging

from locust import HttpUser, between, task

logger = logging.getLogger(__name__)


class SentinelVLoadTestUser(HttpUser):
    """Locust performance & sustained load testing suite for SENTINEL-V (SPEC §16, §23).

    Benchmarks sustained screening throughput of >= 100 videos/hour on reference GPU/mock setups
    without queue backlog accumulation or memory leak degradation.
    """

    wait_time = between(1.0, 3.0)
    internal_key = "default_key"

    def on_start(self):
        """Pre-flight check verifying service readiness."""
        res = self.client.get("/healthz")
        if res.status_code != 200:
            logger.warning(f"Healthz check returned non-200 status: {res.status_code}")

    @task(3)
    def submit_and_poll_analysis(self):
        """Submit a video for calibrated screening and poll until completion."""
        # Submit video analysis
        payload = {
            "mode": "auto",
            "policy_id": "pol_strict_v3",
            "source_url": "https://example.com/loadtest_video.mp4",
        }
        res = self.client.post("/v1/analyses", json=payload, name="/v1/analyses [submit]")
        if res.status_code != 202:
            return

        data = res.json()
        analysis_id = data.get("analysis_id")
        if not analysis_id:
            return

        # Poll status
        for _ in range(5):
            poll_res = self.client.get(
                f"/v1/analyses/{analysis_id}",
                name="/v1/analyses/{id} [poll]",
            )
            if poll_res.status_code == 200:
                poll_data = poll_res.json()
                if poll_data.get("status") in ("completed", "failed"):
                    break

        # Fetch evidence artifacts
        self.client.get(
            f"/v1/analyses/{analysis_id}/evidence",
            name="/v1/analyses/{id}/evidence",
        )

        # Download PDF case report
        self.client.get(
            f"/v1/analyses/{analysis_id}/report.pdf",
            name="/v1/analyses/{id}/report.pdf",
        )

    @task(2)
    def test_compat_moderate_endpoint(self):
        """Test SENTINEL platform compatibility endpoint under concurrent load."""
        payload = {
            "post_id": f"locust_post_{self.environment.runner.user_count if self.environment.runner else 1}",
            "video_url": "https://example.com/sentinel_compat_video.mp4",
        }
        headers = {"X-Internal-Key": self.internal_key}
        self.client.post(
            "/compat/moderate/video",
            json=payload,
            headers=headers,
            name="/compat/moderate/video",
        )

    @task(1)
    def test_receipt_verification(self):
        """Test receipt public verification endpoint."""
        self.client.get("/.well-known/sv-keys.json", name="/.well-known/sv-keys.json")
