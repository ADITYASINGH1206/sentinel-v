import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def inspect_c2pa(media_path: str) -> dict[str, Any]:
    """Inspect media file for C2PA provenance manifests and AI disclosure indicators.

    Returns a dictionary conforming to SPEC §9 & UI expectations:
    {
        "present": bool,
        "ai_disclosed": bool,
        "manifest_title": str | None,
        "format": str | None,
        "raw": dict | None,
    }
    """
    if not media_path:
        return {"present": False, "ai_disclosed": False}

    try:
        import c2pa
    except ImportError:
        logger.warning("c2pa-python is not installed; skipping C2PA provenance extraction")
        return {"present": False, "ai_disclosed": False, "error": "c2pa_library_missing"}

    try:
        reader = c2pa.Reader(media_path)
        raw_json_str = reader.json()
        manifest_data = json.loads(raw_json_str) if raw_json_str else {}

        active_manifest = manifest_data.get("active_manifest") or {}
        title = active_manifest.get("title")
        format_type = active_manifest.get("format")

        # Analyze assertions / actions for generative AI disclosures
        # Standards check: digitalSourceType (e.g. trainedAlgorithmicMedia)
        # or generator/synthetic actions in c2pa.actions
        ai_disclosed = False
        raw_lower = raw_json_str.lower()
        ai_indicators = [
            "trainedalgorithmicmedia",
            "algorithmicmedia",
            "compositealgorithmicmedia",
            "synthetic",
            "generative_ai",
            "ai_generator",
            "dall-e",
            "midjourney",
            "stable diffusion",
        ]
        for ind in ai_indicators:
            if ind in raw_lower:
                ai_disclosed = True
                break

        if not ai_disclosed and ("c2pa.created" in raw_lower and "softwareagent" in raw_lower):
            ai_disclosed = True

        return {
            "present": True,
            "ai_disclosed": ai_disclosed,
            "manifest_title": title,
            "format": format_type,
            "raw": manifest_data,
        }
    except Exception:
        # Standard case when media has no C2PA JUMBF store or is non-C2PA media
        return {
            "present": False,
            "ai_disclosed": False,
        }

