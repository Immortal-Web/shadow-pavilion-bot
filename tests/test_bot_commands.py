import asyncio
import os
import sqlite3
import tempfile
import unittest
from types import SimpleNamespace

import bot
import constants
import db
import discord


def run(coro):
    return asyncio.run(coro)


def command(name):
    #this discord.py hands back the Command wrapper, not the function, so fetch the callback
    return bot.tree.get_command(name, guild=discord.Object(id=constants.GUILD_TOKEN)).callback


class FakeResponse:
    def __init__(self):
        self.sent = []

    async def send_message(self, content, **kwargs):
        self.sent.append(content)


class FakeInterac:
    #duck-typed enough for the command callbacks in bot.py
    def __init__(self, roles=()):
        self.response = FakeResponse()
        self.guild = SimpleNamespace(roles=list(roles))


class RawTests(unittest.TestCase):
    def test_raw_select_returns_rows_and_writes_return_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            daba = db.dbthingy(os.path.join(tmp, "t.db"))
            daba.SetupDB()
            self.assertIsNone(daba.raw("INSERT INTO Users VALUES ('1','a','A')"))
            self.assertEqual(daba.raw("SELECT username FROM Users"), [("a",)])
            daba.finish()  #open handle would lock the temp file on windows

    def test_raw_bad_sql_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            daba = db.dbthingy(os.path.join(tmp, "t.db"))
            daba.SetupDB()
            with self.assertRaises(sqlite3.Error):
                daba.raw("SELEC nope FROM Users")
            daba.finish()  #same here


class CommandTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.daba = db.dbthingy(os.path.join(self._tmp.name, "t.db"))
        self.daba.SetupDB()
        bot.client.daba = self.daba  #commands reach the db through tree.client

    def tearDown(self):
        self.daba.finish()
        self._tmp.cleanup()

    def test_direct_sql_reports_rows(self):
        self.daba.addRecord("Users", db.easy_user_str(1, "bob", "Bob"))
        interac = FakeInterac(roles=[SimpleNamespace(name=constants.ROLE, mention="@Shadow pavilion")])
        run(command("direct_sql")(interac, "SELECT username FROM Users"))
        self.assertEqual(len(interac.response.sent), 1)
        self.assertIn("bob", interac.response.sent[0])
        self.assertIn("@Shadow pavilion", interac.response.sent[0])  #role alert kept

    def test_direct_sql_bad_query_gets_an_answer_not_silence(self):
        interac = FakeInterac(roles=[])
        run(command("direct_sql")(interac, "SELEC nope"))
        self.assertEqual(len(interac.response.sent), 1)
        self.assertIn("sql error", interac.response.sent[0])

    def test_add_explanation_failure_is_reported(self):
        #values that fail the validation regex (newline) must not claim success
        interac = FakeInterac()
        run(command("add_explanation")(interac, 1, "line one\nline two"))
        self.assertEqual(interac.response.sent, ["failed to add (bad characters? blank?)"])

    def test_add_explanation_success_round_trips(self):
        self.daba.addRecord("Users", db.easy_user_str(1, "a", "A"))
        self.daba.addRecord("Nicknames", db.easy_nickn_str(1, "bob"))
        nickn_id = self.daba.rdRecords("Nicknames", "nickn_id", "WHERE nickname = 'bob'")[0][0]
        interac = FakeInterac()
        run(command("add_explanation")(interac, nickn_id, "he's the man"))
        self.assertIn("added", interac.response.sent[0])
        rows = self.daba.rdRecords("Explanations", "explanation", f"WHERE nickn_id = {nickn_id}")
        self.assertEqual(rows, [("he's the man",)])

    def test_every_sensitive_command_has_the_role_check(self):
        #has_role only gates at runtime; this catches a decorator going missing again
        src = open("bot.py", encoding="utf-8").read()
        for name in ("slashgetall", "slashdumptable", "slashaddexpl", "slashemergsql"):
            up_to_def = src[:src.index(f"async def {name}")]
            decorators = up_to_def.split("@tree.command")[-1]
            self.assertIn("has_role", decorators, f"{name} lost its role check")


if __name__ == "__main__":
    unittest.main()
