"""Tests for one-time Telegram account-linking tokens and tenant isolation."""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from v2 import auth, telegram_linking


class TelegramLinkingTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "telegram.sqlite3"
        auth.init_auth_schema(self.db_path)
        telegram_linking.init_schema(self.db_path)
        self.user_a = auth.create_user(self.db_path, "a@example.com", "user-a-password-long")
        self.user_b = auth.create_user(self.db_path, "b@example.com", "user-b-password-long")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_token_links_private_chat_to_owning_user_once(self):
        token, expires_at = telegram_linking.create_link_token(self.db_path, self.user_a["id"], now=100)
        self.assertEqual(expires_at, 100 + telegram_linking.TOKEN_TTL_SECONDS)
        self.assertEqual(telegram_linking.consume_link_token(self.db_path, token, "123456", now=101), self.user_a["id"])
        self.assertEqual(telegram_linking.consume_link_token(self.db_path, token, "123456", now=102), None)
        self.assertTrue(telegram_linking.get_connection(self.db_path, self.user_a["id"])["connected"])
        self.assertIsNone(telegram_linking.get_connection(self.db_path, self.user_b["id"]))

    def test_new_link_token_invalidates_previous_pending_token_for_same_user(self):
        old_token, _ = telegram_linking.create_link_token(self.db_path, self.user_a["id"], now=100)
        new_token, _ = telegram_linking.create_link_token(self.db_path, self.user_a["id"], now=101)
        self.assertIsNone(telegram_linking.consume_link_token(self.db_path, old_token, "123456", now=102))
        self.assertEqual(telegram_linking.consume_link_token(self.db_path, new_token, "123456", now=102), self.user_a["id"])

    def test_expired_unknown_and_malformed_tokens_are_rejected(self):
        token, _ = telegram_linking.create_link_token(self.db_path, self.user_a["id"], now=100)
        self.assertIsNone(telegram_linking.consume_link_token(self.db_path, token, "123456", now=100 + telegram_linking.TOKEN_TTL_SECONDS + 1))
        self.assertIsNone(telegram_linking.consume_link_token(self.db_path, "unknown-token-value-123456", "123456", now=101))
        self.assertIsNone(telegram_linking.consume_link_token(self.db_path, "short", "123456", now=101))

    def test_only_private_chats_can_be_linked(self):
        token, _ = telegram_linking.create_link_token(self.db_path, self.user_a["id"], now=100)
        self.assertIsNone(telegram_linking.consume_link_token(self.db_path, token, "-100123456", "group", now=101))
        self.assertIsNone(telegram_linking.get_connection(self.db_path, self.user_a["id"]))
        self.assertEqual(telegram_linking.consume_link_token(self.db_path, token, "123456", "private", now=102), self.user_a["id"])

    def test_chat_id_cannot_be_linked_to_two_accounts(self):
        token_a, _ = telegram_linking.create_link_token(self.db_path, self.user_a["id"], now=100)
        token_b, _ = telegram_linking.create_link_token(self.db_path, self.user_b["id"], now=100)
        self.assertEqual(telegram_linking.consume_link_token(self.db_path, token_a, "123456", now=101), self.user_a["id"])
        with self.assertRaises(ValueError):
            telegram_linking.consume_link_token(self.db_path, token_b, "123456", now=102)
        # Failed uniqueness must roll back token consumption, so the intended user can retry another chat.
        self.assertEqual(telegram_linking.consume_link_token(self.db_path, token_b, "654321", now=103), self.user_b["id"])

    def test_relink_and_disconnect_are_user_scoped(self):
        first, _ = telegram_linking.create_link_token(self.db_path, self.user_a["id"], now=100)
        second, _ = telegram_linking.create_link_token(self.db_path, self.user_a["id"], now=101)
        telegram_linking.consume_link_token(self.db_path, first, "123456", now=102)
        telegram_linking.consume_link_token(self.db_path, second, "654321", now=103)
        self.assertTrue(telegram_linking.get_connection(self.db_path, self.user_a["id"])["connected"])
        self.assertTrue(telegram_linking.disconnect(self.db_path, self.user_a["id"]))
        self.assertFalse(telegram_linking.disconnect(self.db_path, self.user_a["id"]))
        self.assertIsNone(telegram_linking.get_connection(self.db_path, self.user_a["id"]))

    def test_disconnect_turns_off_member_notifications(self):
        from v2 import user_notifications
        user_notifications.init_schema(self.db_path)
        token, _ = telegram_linking.create_link_token(self.db_path, self.user_a["id"], now=100)
        telegram_linking.consume_link_token(self.db_path, token, "123456", now=101)
        user_notifications.set_enabled(self.db_path, self.user_a["id"], True)
        self.assertTrue(telegram_linking.disconnect(self.db_path, self.user_a["id"]))
        self.assertFalse(user_notifications.get_settings(self.db_path, self.user_a["id"])["enabled"])

    def test_database_stores_only_token_hash(self):
        token, _ = telegram_linking.create_link_token(self.db_path, self.user_a["id"], now=100)
        with sqlite3.connect(self.db_path) as connection:
            stored = connection.execute("SELECT token_hash FROM telegram_link_tokens").fetchone()[0]
        self.assertNotEqual(stored, token)
        self.assertEqual(len(stored), 64)


if __name__ == "__main__":
    unittest.main()
