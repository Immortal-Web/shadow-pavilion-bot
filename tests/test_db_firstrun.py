import asyncio  # noqa: F401  (bot.py imports discord, which needs it available anyway)
import os
import tempfile
import unittest
from types import SimpleNamespace

import bot
import db


class FirstRunTests(unittest.TestCase):
    def test_firstrun_twice_is_safe_and_dedupes(self):
        with tempfile.TemporaryDirectory() as tmp:
            members = [
                SimpleNamespace(id=1, name="a", global_name="A", nick="ace"),
                SimpleNamespace(id=2, name="it's b", global_name=None, nick=None),
            ]
            fake_guild = SimpleNamespace(members=members)
            original = db.DB_FILENAM
            db.DB_FILENAM = os.path.join(tmp, "t.db")
            try:
                client = bot.botman(intents=bot.intents)
                client.get_guild = lambda guild_id: fake_guild

                client.firstRun_setup()
                client.firstRun_setup()  #R3: used to die on IntegrityError here

                rows = client.daba.rdRecords("Users", "user_id, username", "ORDER BY user_id")
                self.assertEqual(rows, [("1", "a"), ("2", "it's b")])  #deduped, not duplicated
                #firstrun also grabs current nicks; nickless members are skipped (no 'None' rows)
                nicks = client.daba.rdRecords("Nicknames", "user_id, nickname", "ORDER BY nickn_id")
                self.assertEqual(nicks, [("1", "ace"), ("1", "ace")])  #one per run — Nicknames is append-only
                client.daba.finish()
            finally:
                db.DB_FILENAM = original  #CRITICAL: never leave this pointing into tmp-less reality


if __name__ == "__main__":
    unittest.main()
