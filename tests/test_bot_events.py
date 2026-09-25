import asyncio
import json
import os
import tempfile
import unittest
from types import SimpleNamespace

import bot
import constants
import db


def run(coro):
    return asyncio.run(coro)


class MemberUpdateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.daba = db.dbthingy(os.path.join(self._tmp.name, "t.db"))
        self.daba.SetupDB()
        self.daba.addRecord("Users", db.easy_user_str(1, "oldname", "OldDisp"))
        self.client = bot.botman(intents=bot.intents)
        self.client.daba = self.daba
        #the live journal goes to a temp file too — never the repo's real one
        self._original_live = constants.LIVE_LOG_FILENAM
        constants.LIVE_LOG_FILENAM = os.path.join(self._tmp.name, "livenicks.jsonl")

    def tearDown(self):
        constants.LIVE_LOG_FILENAM = self._original_live
        self.daba.finish()
        self._tmp.cleanup()

    def member(self, **kw):
        base = dict(id=1, nick=None, name="oldname", global_name="OldDisp")
        base.update(kw)
        return SimpleNamespace(**base)

    def test_nick_with_apostrophe_is_logged(self):
        run(self.client.on_member_update(self.member(), self.member(nick="it's new")))
        rows = self.daba.rdRecords("Nicknames", "nickname", "WHERE user_id = '1'")
        self.assertEqual(rows, [("it's new",)])

    def test_nick_change_is_journaled_to_the_live_log(self):
        #the db has no timestamps, so the journal is what dates this rename later
        run(self.client.on_member_update(self.member(nick="old"), self.member(nick="new nick")))
        with open(constants.LIVE_LOG_FILENAM, encoding="utf-8") as f:
            evs = [json.loads(line) for line in f if line.strip()]
        self.assertEqual(len(evs), 1)
        self.assertEqual((evs[0]["user_id"], evs[0]["before"], evs[0]["after"]),
                         ("1", "old", "new nick"))
        self.assertIn("time", evs[0])

    def test_nick_removal_is_not_journaled(self):
        run(self.client.on_member_update(self.member(nick="old"), self.member(nick=None)))
        self.assertFalse(os.path.exists(constants.LIVE_LOG_FILENAM))

    def test_nick_removal_is_not_logged_as_the_word_None(self):
        run(self.client.on_member_update(self.member(nick="old"), self.member(nick=None)))
        rows = self.daba.rdRecords("Nicknames", "nickname", "")
        self.assertEqual(rows, [])

    def test_username_change_updates_users_row(self):
        run(self.client.on_member_update(
            self.member(),
            self.member(name="newname", global_name="NewDisp")))
        rows = self.daba.rdRecords("Users", "username, display_name", "WHERE user_id = '1'")
        self.assertEqual(rows, [("newname", "NewDisp")])

    def test_global_name_none_lands_as_null_not_the_word_none(self):
        run(self.client.on_member_update(
            self.member(),
            self.member(global_name=None)))
        rows = self.daba.rdRecords("Users", "display_name", "WHERE user_id = '1'")
        self.assertEqual(rows, [(None,)])

    def test_nothing_happens_on_irrelevant_changes(self):
        run(self.client.on_member_update(self.member(), self.member()))  #identical: no writes
        self.assertEqual(self.daba.rdRecords("Nicknames", "nickn_id", ""), [])


class MemberJoinTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.daba = db.dbthingy(os.path.join(self._tmp.name, "t.db"))
        self.daba.SetupDB()
        self.client = bot.botman(intents=bot.intents)
        self.client.daba = self.daba

    def tearDown(self):
        self.daba.finish()
        self._tmp.cleanup()

    def test_rejoining_member_does_not_crash_or_duplicate(self):
        #leave and rejoin: the second insert would explode on the Users primary key
        member = SimpleNamespace(id=1, name="a", global_name="A")
        run(self.client.on_member_join(member))
        run(self.client.on_member_join(member))  #rejoin must not raise
        rows = self.daba.rdRecords("Users", "user_id", "WHERE user_id = '1'")
        self.assertEqual(rows, [("1",)])  #still exactly one row


if __name__ == "__main__":
    unittest.main()
