import logging
import sys
from pathlib import Path

from config import settings

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from storage.kv_store import open_kv_client

logger = logging.getLogger(__name__)

_client = None


async def get_redis():
    global _client
    if _client is None:
        _client = await open_kv_client(settings.REDIS_URL, ROOT_DIR)
        logger.info("Bot KV store ready: %s", type(_client).__name__)
    return _client
