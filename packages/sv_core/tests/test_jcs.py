import json
from sv_core.jcs import canonicalize_json
from sv_core.hashing import sha256_bytes


def test_jcs_key_sorting():
    obj1 = {"z": 1, "a": 2, "m": {"b": True, "a": False}}
    obj2 = {"a": 2, "m": {"a": False, "b": True}, "z": 1}
    
    b1 = canonicalize_json(obj1)
    b2 = canonicalize_json(obj2)
    
    assert b1 == b2
    assert b1 == b'{"a":2,"m":{"a":false,"b":true},"z":1}'


def test_jcs_hashing_stability():
    payload = {
        "receipt_id": "rcpt_01JCX",
        "scores": {"u": 1.66, "p_bal": 0.62},
        "decision": "needs_review"
    }
    canonical = canonicalize_json(payload)
    digest = sha256_bytes(canonical)
    assert len(digest) == 64
