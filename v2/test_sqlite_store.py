from __future__ import annotations

import tempfile
import unittest
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from v2.sqlite_store import SQLITE_BUSY_TIMEOUT_MS, connect, enable_wal


class SQLiteStoreTests(unittest.TestCase):
    def test_connections_use_consistent_busy_timeout_and_wal_is_enabled(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "radar.sqlite3"
            connection = connect(database)
            try:
                self.assertEqual(
                    connection.execute("PRAGMA busy_timeout").fetchone()[0],
                    SQLITE_BUSY_TIMEOUT_MS,
                )
                self.assertEqual(enable_wal(connection), "wal")
            finally:
                connection.close()

            reopened = connect(database)
            try:
                self.assertEqual(
                    reopened.execute("PRAGMA journal_mode").fetchone()[0], "wal"
                )
                self.assertEqual(
                    reopened.execute("PRAGMA busy_timeout").fetchone()[0],
                    SQLITE_BUSY_TIMEOUT_MS,
                )
            finally:
                reopened.close()

    def test_writer_waits_for_another_connection_within_busy_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "contended.sqlite3"
            setup = connect(database)
            setup.execute("CREATE TABLE counter (value INTEGER NOT NULL)")
            setup.execute("INSERT INTO counter VALUES (0)")
            setup.commit()
            enable_wal(setup)
            setup.execute("BEGIN IMMEDIATE")

            attempting_write = threading.Event()

            def second_writer():
                connection = connect(database)
                try:
                    attempting_write.set()
                    connection.execute("UPDATE counter SET value=value+1")
                    connection.commit()
                finally:
                    connection.close()

            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(second_writer)
                    self.assertTrue(attempting_write.wait(timeout=2))
                    time.sleep(0.15)
                    setup.execute("UPDATE counter SET value=value+1")
                    setup.commit()
                    future.result(timeout=3)
            finally:
                setup.close()

            check = connect(database)
            try:
                self.assertEqual(check.execute("SELECT value FROM counter").fetchone()[0], 2)
            finally:
                check.close()


if __name__ == "__main__":
    unittest.main()
