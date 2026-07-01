"""
File-based JSON cache for Parse.bot API responses.

Cache key = SHA-256 of (endpoint + sorted params).
Files live in ./cache/<key>.json with an embedded expiry timestamp.
"""

import hashlib
import json
import os
import time
from typing import Any, Optional


CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")


class FileCache:
    def __init__(self, ttl_minutes: int = 60):
        self.ttl_seconds = ttl_minutes * 60
        os.makedirs(CACHE_DIR, exist_ok=True)

    # ──────────────────────────────────────────────
    # PUBLIC
    # ──────────────────────────────────────────────

    def make_key(self, endpoint: str, params: dict) -> str:
        raw = endpoint + json.dumps(params, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        path = self._path(key)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                envelope = json.load(f)
            if time.time() > envelope["expires_at"]:
                os.remove(path)
                return None
            return envelope["data"]
        except (json.JSONDecodeError, KeyError, OSError):
            return None

    def set(self, key: str, data: Any) -> None:
        envelope = {
            "expires_at": time.time() + self.ttl_seconds,
            "data": data,
        }
        path = self._path(key)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(envelope, f, ensure_ascii=False)

    def clear(self) -> int:
        removed = 0
        for fname in os.listdir(CACHE_DIR):
            if fname.endswith(".json"):
                try:
                    os.remove(os.path.join(CACHE_DIR, fname))
                    removed += 1
                except OSError:
                    pass
        return removed

    # ──────────────────────────────────────────────
    # PRIVATE
    # ──────────────────────────────────────────────

    def _path(self, key: str) -> str:
        return os.path.join(CACHE_DIR, f"{key}.json")
