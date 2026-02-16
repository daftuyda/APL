import json
import os
import time
import shutil

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.cache')
DEFAULT_TTL = 3600       # 1 hour for user list data
RELATIONS_TTL = 604800   # 7 days for relation data (rarely changes)


class Cache:
    def __init__(self):
        os.makedirs(CACHE_DIR, exist_ok=True)

    def _path(self, namespace, key):
        safe_key = str(key).replace('/', '_').replace('\\', '_')
        ns_dir = os.path.join(CACHE_DIR, namespace)
        os.makedirs(ns_dir, exist_ok=True)
        return os.path.join(ns_dir, f"{safe_key}.json")

    def get(self, namespace, key, ttl=DEFAULT_TTL):
        path = self._path(namespace, key)
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                entry = json.load(f)
            if time.time() - entry['ts'] > ttl:
                return None
            return entry['data']
        except (json.JSONDecodeError, KeyError, IOError):
            return None

    def set(self, namespace, key, data):
        path = self._path(namespace, key)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'ts': time.time(), 'data': data}, f)

    def clear(self):
        if os.path.exists(CACHE_DIR):
            shutil.rmtree(CACHE_DIR)
        os.makedirs(CACHE_DIR, exist_ok=True)

    def age(self, namespace, key):
        """Returns cache age in seconds, or None if not cached."""
        path = self._path(namespace, key)
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                entry = json.load(f)
            return time.time() - entry['ts']
        except (json.JSONDecodeError, KeyError, IOError):
            return None


cache = Cache()
