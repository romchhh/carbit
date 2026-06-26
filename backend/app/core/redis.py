import sys
from pathlib import Path

from app.core.config import settings

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from storage.kv_store import get_kv_client

_client = None


async def get_redis():
    global _client
    if _client is None:
        _client = get_kv_client(settings.REDIS_URL, ROOT_DIR)
    return _client
