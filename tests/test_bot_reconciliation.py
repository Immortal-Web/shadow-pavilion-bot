import asyncio
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import bot
import constants
import db
import discord

from tests.test_bot_commands import FakeInterac, command


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.daba = db.dbthingy(os.path.join(tmp.name, "t.db"))
        self.addCleanup(self.daba.finish)
        self.daba.SetupDB()
        self.client = bot.botman(intents=bot.intents)
        self.client.daba = self.daba
        self.live = os.path.join(tmp.name, "livenicks.jsonl")
        #neither the date cache nor the commands should touch real member files
        for target, name, value in (
            (constants, "LIVE_LOG_FILENAM", self.live),
            (bot, "dump_filnam", lambda cid: os.path.join(tmp.name, "missing.jsonl")),
            (bot, "_nick_times", {"dump_mtime": None, "live_mtime": None, "dump_map": {}, "live_map": {}}),
            (bot.client, "daba", self.daba),
        ):
            patcher = patch.object(target, name, value, create=True)
            patcher.start()
            self.addCleanup(patcher.stop)

        self.fresh_members = [self.member(1, "caPoo"), self.member(2, "it's new"), self.member(3, None)]
        self.fetch_error = False

        async def fetch_members(*, limit):
            self.assertIsNone(limit)  #all pages, not discord.py's default limit of 1000
            yield self.fresh_members[0]
            if self.fetch_error:
                raise discord.HTTPException(SimpleNamespace(status=503, reason="unavailable"), "try later")
            for member in self.fresh_members[1:]:
                yield member

        #the cache deliberately disagrees with the fresh roster
        guild = SimpleNamespace(members=[self.member(1, "stale")], fetch_members=fetch_members)

        def get_guild(guild_id):
            self.assertEqual(guild_id, constants.GUILD_TOKEN)
            return guild

        self.client.get_guild = get_guild

    def member(self, uid, nick):
        return SimpleNamespace(id=uid, nick=nick, name=f"user{uid}", global_name=None,
                               display_name=nick or f"user{uid}")

    def test_ready_recovers_current_nicknames_from_fresh_roster(self):
        asyncio.run(self.client.on_ready())
        self.assertEqual(self.daba.rdRecords("Nicknames", "user_id, nickname", "ORDER BY nickn_id"),
                         [("1", "caPoo"), ("2", "it's new")])
        self.assertEqual(self.daba.rdRecords("Users", "user_id", "ORDER BY user_id"),
                         [("1",), ("2",), ("3",)])
        self.assertFalse(os.path.exists(self.live))

    def test_resume_recovers_missed_change_once_and_displays_it_undated(self):
        async def reconnects():
            await self.client.on_ready()
            #no on_member_update: the rename happened while disconnected
            self.fresh_members[0] = self.member(1, "missed nick")
            await self.client.on_resumed()
            await self.client.on_resumed()
            await self.client.on_ready()  #also safe after a full new gateway session

        asyncio.run(reconnects())
        self.assertEqual(self.daba.rdRecords("Nicknames", "nickn_id, nickname", "WHERE user_id = '1' ORDER BY nickn_id"),
                         [(1, "caPoo"), (3, "missed nick")])
        self.assertFalse(os.path.exists(self.live))
        interac = FakeInterac()
        asyncio.run(command("print_nicknames")(interac, self.member(1, "missed nick"), True))
        self.assertEqual(interac.response.embeds[0].description,
                         "`#1` `(undated)` caPoo\n`#2` `(undated)` missed nick")

    def test_reconciliation_does_not_date_an_existing_undated_nickname(self):
        self.daba.addRecord("Users", db.easy_user_str(1, "user1", None))
        self.daba.addRecord("Nicknames", db.easy_nickn_str(1, "caPoo"))
        asyncio.run(self.client.on_ready())
        self.assertEqual(bot.user_nick_rows(self.daba, self.member(1, "caPoo")), [(1, "caPoo", None)])
        self.assertFalse(os.path.exists(self.live))

    def test_reusing_recovered_names_preserves_display_indexes_and_explanations(self):
        async def recover_and_reuse():
            await self.client.on_ready()
            for nick in ("second", "third"):
                self.fresh_members[0] = self.member(1, nick)
                await self.client.on_resumed()
            self.daba.addRecord("Explanations", db.easy_expln_str(3, "belongs to second"))
            #the live event is real, but neither name's original rename time is known
            await self.client.on_member_update(self.member(1, "third"), self.member(1, "caPoo"))

        asyncio.run(recover_and_reuse())
        self.assertTrue(os.path.exists(self.live))  #reuse is still journaled
        self.assertEqual(bot.user_nick_rows(self.daba, self.member(1, "caPoo")),
                         [(1, "caPoo", None), (3, "second", None), (4, "third", None)])
        interac = FakeInterac()
        asyncio.run(command("explain_nickname")(interac, self.member(1, "caPoo"), 2, True))
        self.assertIn("#2 — second", interac.response.sent[0])
        self.assertIn("belongs to second", interac.response.sent[0])

    def test_new_live_nickname_gets_a_date_without_dating_recovered_before_name(self):
        async def recover_then_change():
            await self.client.on_ready()
            await self.client.on_member_update(self.member(1, "caPoo"), self.member(1, "new live"))

        asyncio.run(recover_then_change())
        seen = bot.nick_first_seen()
        self.assertNotIn(("1", "caPoo"), seen)
        self.assertIn(("1", "new live"), seen)

    def test_failed_fetch_can_recover_on_next_reconnect(self):
        self.fetch_error = True
        asyncio.run(self.client.on_ready())
        self.assertEqual(self.daba.rdRecords("Nicknames", "*", ""), [])
        self.fetch_error = False
        asyncio.run(self.client.on_ready())
        self.assertEqual(self.daba.rdRecords("Nicknames", "user_id, nickname", "ORDER BY nickn_id"),
                         [("1", "caPoo"), ("2", "it's new")])

    def test_missing_guild_leaves_database_alone(self):
        self.client.get_guild = lambda guild_id: None
        asyncio.run(self.client.on_ready())
        self.assertEqual(self.daba.rdRecords("Users", "*", ""), [])


if __name__ == "__main__":
    unittest.main()
