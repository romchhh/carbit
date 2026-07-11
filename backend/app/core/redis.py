import logging
import sys
from pathlib import Path

from app.core.config import settings

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from storage.kv_store import open_kv_client

logger = logging.getLogger(__name__)

_client = None


async def get_redis():
    global _client
    if _client is None:
        _client = await open_kv_client(settings.REDIS_URL, ROOT_DIR)
        kind = type(_client).__name__
        logger.info("KV store ready: %s (REDIS_URL=%s)", kind, settings.REDIS_URL)
    return _client
