import os
import tempfile
import unittest

import bot
import db


class SetupHookTests(unittest.TestCase):
    def test_setup_hook_opens_db_and_syncs_exactly_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            original_db = db.DB_FILENAM
            original_sync = bot.tree.sync
            calls = []

            async def fake_sync(**kwargs):
                calls.append(kwargs)

            db.DB_FILENAM = os.path.join(tmp, "t.db")
            bot.tree.sync = fake_sync  #instance attribute shadows the bound method; no network
            try:
                client = bot.botman(intents=bot.intents)
                import asyncio
                asyncio.run(client.setup_hook())
                self.assertEqual(len(calls), 1)
                self.assertIsNotNone(client.daba)
                self.assertTrue(os.path.exists(db.DB_FILENAM))
                client.daba.finish()
            finally:
                db.DB_FILENAM = original_db
                bot.tree.sync = original_sync  #don't poison other tests in the same process


if __name__ == "__main__":
    unittest.main()
