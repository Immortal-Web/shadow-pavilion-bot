import asyncio
import os
import tempfile
import unittest
from types import SimpleNamespace

import bot
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

    def tearDown(self):
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


if __name__ == "__main__":
    unittest.main()
