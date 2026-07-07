"""
Структура даних оголошення про авто.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class CarListing:
    # ідентифікація джерела
    channel: str                       # @username каналу
    message_id: int                    # id першого повідомлення (або групи-альбому)
    group_message_ids: list            # всі id повідомлень, що входять в оголошення (альбом)
    source_link: str                   # пряме посилання t.me/channel/id
    posted_at: Optional[datetime]

    # сирий текст - завжди зберігаємо, навіть якщо парсинг не вдався
    raw_text: str

    # розпізнані поля (можуть бути None, якщо не вдалось витягти)
    brand: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    price_amount: Optional[float] = None
    price_currency: Optional[str] = None       # USD / EUR / UAH
    mileage_km: Optional[int] = None
    engine_volume_l: Optional[float] = None
    power_hp: Optional[int] = None
    transmission: Optional[str] = None          # manual / automatic / robot / variator
    drive_type: Optional[str] = None            # fwd / rwd / awd
    fuel_type: Optional[str] = None             # petrol / diesel / gas / hybrid / electric
    location_city: Optional[str] = None
    phone: Optional[str] = None
    contact_username: Optional[str] = None

    # прапорці зі стану авто (не бита/не крашена/розмитнена і т.д.), якщо згадано в тексті
    condition_flags: dict = field(default_factory=dict)

    # локальні шляхи до завантажених фото цього оголошення
    photos: list = field(default_factory=list)

    # 0..1, наскільки впевнено ми розпарсили оголошення (див. extractor.py)
    confidence: float = 0.0
    # якщо True - варто показати оголошення людині для ручної перевірки/донабору полів
    needs_review: bool = True

    def to_dict(self) -> dict:
        d = asdict(self)
        if self.posted_at:
            d["posted_at"] = self.posted_at.isoformat()
        return d