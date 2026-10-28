import json
from typing import Any

try:
    import rfc8785
    HAS_RFC8785 = True
except ImportError:
    HAS_RFC8785 = False


def canonicalize_json(data: Any) -> bytes:
    """Canonicalize a Python object into bytes according to RFC 8785 (JCS)."""
    if HAS_RFC8785:
        return rfc8785.dumps(data)
    
    # Fallback deterministic canonical JSON serializer
    def serialize(obj: Any) -> str:
        if obj is None:
            return "null"
        elif isinstance(obj, bool):
            return "true" if obj else "false"
        elif isinstance(obj, (int, float)):
            if isinstance(obj, float) and (obj != obj or obj == float("inf") or obj == float("-inf")):
                raise ValueError("NaN and Infinity are not supported in JSON")
            # Format float deterministically
            if isinstance(obj, float) and obj.is_integer():
                return f"{int(obj)}"
            return f"{obj}"
        elif isinstance(obj, str):
            return json.dumps(obj, ensure_ascii=False)
        elif isinstance(obj, (list, tuple)):
            return "[" + ",".join(serialize(item) for item in obj) + "]"
        elif isinstance(obj, dict):
            # Sort keys lexicographically according to RFC 8785
            sorted_keys = sorted(obj.keys())
            items = [f"{json.dumps(k, ensure_ascii=False)}:{serialize(obj[k])}" for k in sorted_keys]
            return "{" + ",".join(items) + "}"
        else:
            raise TypeError(f"Type {type(obj)} not serializable in RFC 8785")

    return serialize(data).encode("utf-8")
