"""Тести парсингу описів для фільтра ДТП (REONO, Car Market)."""

from __future__ import annotations

import unittest

from app.services.car_market.detail import parse_detail_description as parse_car_market_description
from app.services.reono.detail import parse_detail_description as parse_reono_description


REONO_HTML = """
<html><body>
<div class="about-car-main__content">
  Автомобіль в непоганому стані. В ДТП небув. Другий власник.
</div>
<script type="application/ld+json">
{"@type":"Car","description":"ignored when content exists"}
</script>
</body></html>
"""

CAR_MARKET_HTML = """
<html><body>
<div class="px-4 py-4 text-surface-600 text-sm leading-relaxed">
  Шикарний стан авто. Без ДТП. Рідний пробіг.
</div>
</body></html>
"""


class ScrapedDescriptionParserTests(unittest.TestCase):
    def test_reono_detail_description(self):
        text = parse_reono_description(REONO_HTML)
        self.assertIn("ДТП небув", text or "")

    def test_car_market_detail_description(self):
        text = parse_car_market_description(CAR_MARKET_HTML)
        self.assertIn("Без ДТП", text or "")


if __name__ == "__main__":
    unittest.main()
