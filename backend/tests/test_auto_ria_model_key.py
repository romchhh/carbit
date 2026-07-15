from __future__ import annotations

import unittest

from app.services.auto_ria.catalog import _normalize_model_key


class AutoRiaModelKeyTests(unittest.TestCase):
    def test_coupe_aliases(self):
        self.assertEqual(_normalize_model_key("GLE Coupe"), "gle coupe")
        self.assertEqual(_normalize_model_key("GLE-Class Coupe"), "gle coupe")
        self.assertEqual(_normalize_model_key("GLE (купе)"), "gle coupe")
        self.assertEqual(_normalize_model_key("GLC-Class Coupe"), "glc coupe")
        self.assertEqual(_normalize_model_key("CLE-Class"), "cle")


if __name__ == "__main__":
    unittest.main()
