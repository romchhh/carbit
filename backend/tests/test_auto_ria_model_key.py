from __future__ import annotations

import unittest

from app.services.auto_ria.catalog import _model_catalog_match, _normalize_model_key


class AutoRiaModelKeyTests(unittest.TestCase):
    def test_coupe_aliases(self):
        self.assertEqual(_normalize_model_key("GLE Coupe"), "gle coupe")
        self.assertEqual(_normalize_model_key("GLE-Class Coupe"), "gle coupe")
        self.assertEqual(_normalize_model_key("GLE (купе)"), "gle coupe")
        self.assertEqual(_normalize_model_key("GLC-Class Coupe"), "glc coupe")
        self.assertEqual(_normalize_model_key("CLE-Class"), "cle")

    def test_c_class_coupe_not_glc_partial(self):
        target = "C-Class Coupe"
        target_key = _normalize_model_key(target)
        self.assertFalse(
            _model_catalog_match(
                target,
                target_key,
                "GLC-Class Coupe",
                "glc-class coupe",
                _normalize_model_key("GLC-Class Coupe"),
            )
        )
        self.assertTrue(
            _model_catalog_match(
                target,
                target_key,
                "C-Class Coupe",
                "c-class coupe",
                _normalize_model_key("C-Class Coupe"),
            )
        )


if __name__ == "__main__":
    unittest.main()
