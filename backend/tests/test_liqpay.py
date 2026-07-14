"""LiqPay encode / verify."""

from __future__ import annotations

import base64
import json
import unittest
from unittest.mock import patch

from app.services.billing import liqpay as liqpay_mod


class LiqPayCryptoTests(unittest.TestCase):
    def test_encode_and_verify_roundtrip(self):
        with patch.object(liqpay_mod.settings, "LIQPAY_PUBLIC_KEY", "sandbox_pub"), patch.object(
            liqpay_mod.settings, "LIQPAY_PRIVATE_KEY", "sandbox_priv"
        ):
            data, signature = liqpay_mod.encode_checkout(
                {
                    "action": "subscribe",
                    "amount": 390,
                    "currency": "UAH",
                    "description": "test",
                    "order_id": "carbit_lite_test_1",
                    "subscribe": "1",
                    "subscribe_periodicity": "month",
                    "subscribe_date_start": "2026-07-14 12:00:00",
                }
            )
            self.assertTrue(liqpay_mod.verify_callback(data, signature))
            payload = liqpay_mod.decode_data(data)
            self.assertEqual(payload["order_id"], "carbit_lite_test_1")
            self.assertEqual(payload["public_key"], "sandbox_pub")
            self.assertEqual(payload["amount"], 390)

    def test_reject_tampered_signature(self):
        with patch.object(liqpay_mod.settings, "LIQPAY_PUBLIC_KEY", "sandbox_pub"), patch.object(
            liqpay_mod.settings, "LIQPAY_PRIVATE_KEY", "sandbox_priv"
        ):
            data, _ = liqpay_mod.encode_checkout({"action": "subscribe", "order_id": "x"})
            self.assertFalse(liqpay_mod.verify_callback(data, base64.b64encode(b"bad").decode()))

    def test_decode_invalid(self):
        with self.assertRaises(Exception):
            liqpay_mod.decode_data(base64.b64encode(b"not-json").decode())


if __name__ == "__main__":
    unittest.main()
