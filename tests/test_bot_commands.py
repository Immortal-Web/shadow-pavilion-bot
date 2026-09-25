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
        self.kwargs = []
        self.embeds = []

    async def send_message(self, content=None, **kwargs):
        self.sent.append(content)
        self.kwargs.append(kwargs)
        if kwargs.get("embed") is not None:
            self.embeds.append(kwargs["embed"])

    async def send(self, content=None, **kwargs):  #followup pages land here
        self.sent.append(content)
        self.kwargs.append(kwargs)
        if kwargs.get("embed") is not None:
            self.embeds.append(kwargs["embed"])


class FakeInterac:
    #duck-typed enough for the command callbacks in bot.py
    def __init__(self, roles=()):
        self.response = FakeResponse()
        self.followup = FakeResponse()  #paged commands (print_nicknames) overflow into this
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
        self.daba.addRecord("Users", db.easy_user_str(1, "a", "A"))
        self.daba.addRecord("Nicknames", db.easy_nickn_str(1, "bob"))
        user = SimpleNamespace(id=1, display_name="A")
        interac = FakeInterac()
        run(command("add_explanation")(interac, user, 1, "line one\nline two"))
        self.assertEqual(interac.response.sent, ["failed to add (bad characters? blank?)"])

    def test_add_explanation_success_round_trips(self):
        self.daba.addRecord("Users", db.easy_user_str(1, "a", "A"))
        self.daba.addRecord("Nicknames", db.easy_nickn_str(1, "bob"))
        nickn_id = self.daba.rdRecords("Nicknames", "nickn_id", "WHERE nickname = 'bob'")[0][0]
        user = SimpleNamespace(id=1, display_name="A")
        interac = FakeInterac()
        run(command("add_explanation")(interac, user, 1, "he's the man"))
        self.assertIn("added", interac.response.sent[0])
        self.assertIn("#1", interac.response.sent[0])  #points at the per-user number, not the db id
        rows = self.daba.rdRecords("Explanations", "explanation", f"WHERE nickn_id = {nickn_id}")
        self.assertEqual(rows, [("he's the man",)])

    def test_add_explanation_bad_index_gets_an_answer_not_silence(self):
        #an index past the user's list must be answered, not silently ignored
        self.daba.addRecord("Users", db.easy_user_str(1, "a", "A"))
        self.daba.addRecord("Nicknames", db.easy_nickn_str(1, "bob"))
        user = SimpleNamespace(id=1, display_name="A")
        interac = FakeInterac()
        run(command("add_explanation")(interac, user, 999, "explanation"))
        self.assertEqual(len(interac.response.sent), 1)
        self.assertIn("doesn't have that many", interac.response.sent[0])

    def test_every_sensitive_command_has_the_role_check(self):
        #has_role only gates at runtime; this catches a decorator going missing again
        src = open("bot.py", encoding="utf-8").read()
        for name in ("slashgetall", "slashdumptable", "slashaddexpl", "slashemergsql"):
            up_to_def = src[:src.index(f"async def {name}")]
            decorators = up_to_def.split("@tree.command")[-1]
            self.assertIn("has_role", decorators, f"{name} lost its role check")


class CommandWiringTests(unittest.TestCase):
    #the commands that had no callback-level tests: firstrun_init, dump_table,
    #explain_nickname — plus the "#number means the same thing everywhere" invariant
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.daba = db.dbthingy(os.path.join(self._tmp.name, "t.db"))
        self.daba.SetupDB()
        bot.client.daba = self.daba
        self._original_nfs = bot.nick_first_seen
        bot.nick_first_seen = lambda: {}  #don't chew through the real 40k-line dump in here

    def tearDown(self):
        bot.nick_first_seen = self._original_nfs
        self.daba.finish()
        self._tmp.cleanup()

    def test_print_nicknames_with_no_nicks_answers_instead_of_silence(self):
        self.daba.addRecord("Users", db.easy_user_str(1, "a", "A"))
        interac = FakeInterac()
        run(command("print_nicknames")(interac, SimpleNamespace(id=1, display_name="A"), True))
        self.assertEqual(len(interac.response.sent), 1)
        self.assertIn("no nicknames on record", interac.response.sent[0])

    def test_explain_numbering_is_what_print_nicknames_shows(self):
        #print and explain must speak the same #numbers or people explain the wrong nick
        self.daba.addRecord("Users", db.easy_user_str(1, "a", "A"))
        for nick in ("new", "mystery", "old"):
            self.daba.addRecord("Nicknames", db.easy_nickn_str(1, nick))
        bot.nick_first_seen = lambda: {("1", "old"): "25-01-01", ("1", "new"): "26-01-01"}
        user = SimpleNamespace(id=1, display_name="A")

        printed = FakeInterac()
        run(command("print_nicknames")(printed, user, True))
        desc = printed.response.embeds[0].description
        line1 = [l for l in desc.splitlines() if l.startswith("`#1`")]
        self.assertEqual(len(line1), 1)
        self.assertIn("old", line1[0])

        explained = FakeInterac()
        run(command("explain_nickname")(explained, user, 1, True))
        #same nickname, same number, plus the date print promised
        self.assertIn("#1 — old (25-01-01)", explained.response.sent[0])

    def test_add_then_explain_by_number_round_trips(self):
        self.daba.addRecord("Users", db.easy_user_str(1, "a", "A"))
        self.daba.addRecord("Nicknames", db.easy_nickn_str(1, "bob"))
        user = SimpleNamespace(id=1, display_name="A")

        added = FakeInterac()
        run(command("add_explanation")(added, user, 1, "he's the man"))
        self.assertIn("added to #1 'bob'", added.response.sent[0])

        explained = FakeInterac()
        run(command("explain_nickname")(explained, user, 1, True))
        self.assertIn("#1 — bob", explained.response.sent[0])
        self.assertIn("• he's the man", explained.response.sent[0])

    def test_explain_without_explanations_says_so(self):
        self.daba.addRecord("Users", db.easy_user_str(1, "a", "A"))
        self.daba.addRecord("Nicknames", db.easy_nickn_str(1, "bob"))
        interac = FakeInterac()
        run(command("explain_nickname")(interac, SimpleNamespace(id=1, display_name="A"), 1, True))
        self.assertIn("no explanations yet", interac.response.sent[0])

    def test_explain_bad_index_gets_an_answer_not_silence(self):
        self.daba.addRecord("Users", db.easy_user_str(1, "a", "A"))
        self.daba.addRecord("Nicknames", db.easy_nickn_str(1, "bob"))
        interac = FakeInterac()
        run(command("explain_nickname")(interac, SimpleNamespace(id=1, display_name="A"), 5, True))
        self.assertIn("doesn't have that many", interac.response.sent[0])

    def test_firstrun_init_command_actually_sets_up(self):
        original_dbfil = db.DB_FILENAM
        original_get_guild = bot.client.get_guild
        db.DB_FILENAM = os.path.join(self._tmp.name, "firstrun.db")
        #firstRun_setup closes whatever daba it finds on the client, so hand it a
        #throwaway instead of the shared one (tearDown still wants to close that)
        throwaway = db.dbthingy(os.path.join(self._tmp.name, "throwaway.db"))
        bot.client.daba = throwaway
        bot.client.get_guild = lambda gid: SimpleNamespace(members=[
            SimpleNamespace(id=1, name="a", global_name="A", nick="ace"),
            SimpleNamespace(id=2, name="b", global_name=None, nick=None),  #nickless: skipped
        ])
        try:
            interac = FakeInterac()
            run(command("firstrun_init")(interac))
            self.assertIn("setup complete", interac.response.sent[0])
            users = bot.client.daba.rdRecords("Users", "user_id", "ORDER BY user_id")
            self.assertEqual(users, [("1",), ("2",)])
            nicks = bot.client.daba.rdRecords("Nicknames", "nickname", "")
            self.assertEqual(nicks, [("ace",)])  #no 'None' row for the nickless one
        finally:
            bot.client.daba.finish()
            bot.client.daba = self.daba
            bot.client.get_guild = original_get_guild
            db.DB_FILENAM = original_dbfil

    def test_dump_table_sends_the_db_file(self):
        original_dbfil = constants.DB_FILENAM
        constants.DB_FILENAM = os.path.join(self._tmp.name, "t.db")  #exists — setUp made it
        try:
            interac = FakeInterac()
            run(command("dump_table")(interac))
            self.assertEqual(len(interac.response.sent), 1)
            attachment = interac.response.kwargs[0]["file"]
            self.assertEqual(attachment.filename, "nicknames.db")
            self.assertTrue(interac.response.kwargs[0]["ephemeral"])
        finally:
            constants.DB_FILENAM = original_dbfil


if __name__ == "__main__":
    unittest.main()
