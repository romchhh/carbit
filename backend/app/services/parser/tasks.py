from __future__ import annotations

import logging

from app.services.parser.queue import schedule_parse_search

logger = logging.getLogger(__name__)

__all__ = ["schedule_parse_search"]
