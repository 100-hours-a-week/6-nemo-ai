from cachetools import TTLCache

chat_cache = TTLCache(maxsize=1000, ttl=600)

def get_cached_response(query: str) -> str | None:
    return chat_cache.get(query)

def set_cached_response(query: str, response: dict) -> None:
    chat_cache[query] = response