from __future__ import annotations

from app.services.telegram_channels.bootstrap import ensure_parser_path


def get_parser_service(*, fresh_dedupe: bool = False, skip_dedupe: bool = False):
    ensure_parser_path()
    from parser.service import CarParserService

    return CarParserService(fresh_dedupe=fresh_dedupe, skip_dedupe=skip_dedupe)


def get_parser_channels() -> list[str]:
    ensure_parser_path()
    from parser.config import settings

    return list(settings.default_channels)
