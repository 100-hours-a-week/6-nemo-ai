import time
import hashlib

_CACHE = {}
_TTL = 600  # seconds (10 minutes)

def make_cache_key(prefix: str, text: str, model_id: str = "") -> str:

    hashed = hashlib.sha256(text.encode()).hexdigest()
    return f"{prefix}:{model_id}:{hashed}"

def get_cached(key: str):
    entry = _CACHE.get(key)
    if not entry:
        return None

    value, timestamp = entry
    if time.time() - timestamp < _TTL:
        return value

    del _CACHE[key]
    return None

def set_cached(key: str, value: dict):
    _CACHE[key] = (value, time.time())