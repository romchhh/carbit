"""
Обгортка над Telethon: підключення до Telegram, а також перевірка/автовступ
у канал перед парсингом (за твоєю вимогою).
"""
import logging
from telethon import TelegramClient
from telethon.tl.functions.channels import GetParticipantRequest, JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.errors import (
    UserNotParticipantError,
    ChannelPrivateError,
    InviteHashExpiredError,
    InviteHashInvalidError,
    UserAlreadyParticipantError,
    FloodWaitError,
)

from .config import settings

log = logging.getLogger("carbit_parser.client")


def build_client() -> TelegramClient:
    if not settings.api_id or not settings.api_hash:
        raise RuntimeError(
            "TG_API_ID / TG_API_HASH не задані. Візьми їх на https://my.telegram.org "
            "і пропиши у .env"
        )
    return TelegramClient(settings.session_path, settings.api_id, settings.api_hash)


async def ensure_joined(client: TelegramClient, channel: str) -> bool:
    """
    Перевіряє, чи є поточний акаунт учасником каналу/чату.
    Якщо ні - намагається приєднатись (для публічних каналів за @username,
    або за інвайт-посиланням виду t.me/+xxxx / t.me/joinchat/xxxx).

    Повертає True, якщо після виклику акаунт є учасником каналу
    (а отже, історію повідомлень можна читати повноцінно).
    """
    channel = channel.strip()

    # @+HASH або +HASH (приватний інвайт без повного URL)
    if channel.startswith("@+"):
        invite_hash = channel[2:].strip()
        try:
            await client(ImportChatInviteRequest(invite_hash))
            log.info("Приєднався до приватного чату за інвайтом @+%s", invite_hash[:8])
            return True
        except UserAlreadyParticipantError:
            return True
        except (InviteHashExpiredError, InviteHashInvalidError):
            log.warning("Інвайт @+%s недійсний/протермінований", invite_hash[:8])
            return False
        except FloodWaitError as e:
            log.warning("FloodWait %s сек при вступі в @+%s", e.seconds, invite_hash[:8])
            return False
        except Exception as e:
            log.warning("Не вдалось приєднатись за @+%s: %s", invite_hash[:8], e)
            return False

    # приватний інвайт-лінк
    if "joinchat/" in channel or "/+" in channel:
        invite_hash = channel.split("joinchat/")[-1].split("/+")[-1].strip("/")
        try:
            await client(ImportChatInviteRequest(invite_hash))
            log.info("Приєднався до приватного чату за інвайтом %s", channel)
            return True
        except UserAlreadyParticipantError:
            return True
        except (InviteHashExpiredError, InviteHashInvalidError):
            log.warning("Інвайт-посилання недійсне/протерміноване: %s", channel)
            return False
        except FloodWaitError as e:
            log.warning("FloodWait %s сек при вступі в %s", e.seconds, channel)
            return False
        except Exception as e:
            log.warning("Не вдалось приєднатись за інвайтом %s: %s", channel, e)
            return False

    # публічний канал за username
    try:
        entity = await client.get_entity(channel)
    except Exception as e:
        log.warning("Не вдалось знайти канал %s: %s", channel, e)
        return False

    me = await client.get_me()
    try:
        await client(GetParticipantRequest(entity, me))
        return True  # вже учасник
    except UserNotParticipantError:
        try:
            await client(JoinChannelRequest(entity))
            log.info("Приєднався до каналу %s", channel)
            return True
        except FloodWaitError as e:
            log.warning("FloodWait %s сек при вступі в %s", e.seconds, channel)
            return False
        except ChannelPrivateError:
            log.warning("Канал %s приватний, вступ неможливий без інвайту", channel)
            return False
        except Exception as e:
            log.warning("Не вдалось приєднатись до %s: %s", channel, e)
            return False
    except ChannelPrivateError:
        log.warning("Канал %s приватний/недоступний", channel)
        return False
    except Exception as e:
        # деякі супергрупи не підтримують GetParticipantRequest напряму -
        # у цьому разі просто пробуємо вступити, це безпечна операція (не дасть помилки,
        # якщо ти вже учасник)
        log.debug("GetParticipantRequest fallback для %s: %s", channel, e)
        try:
            await client(JoinChannelRequest(entity))
            return True
        except Exception as e2:
            log.warning("Не вдалось приєднатись до %s: %s", channel, e2)
            return False