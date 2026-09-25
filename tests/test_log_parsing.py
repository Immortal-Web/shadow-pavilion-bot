import asyncio
import json
import os
import tempfile
import unittest

import discord

import bot
import constants
import db


def command(name):
    #fetch the callback out of the Command wrapper, same trick as test_bot_commands
    return bot.tree.get_command(name, guild=discord.Object(id=constants.GUILD_TOKEN)).callback


#embed dicts copied from what dyno/carl actually send (probed from the live channel).
#to_dict() omits empty titles, hence no "title" key on the dyno one
def dyno_emb(uid, before, after, action="changed", author="someone"):
    return {"description": f"**<@{uid}> nickname {action}**",
            "fields": [{"name": "Before", "value": before, "inline": False},
                       {"name": "After", "value": after, "inline": False}],
            "footer": {"text": f"ID: {uid}"}, "author": {"name": author}}

def carl_emb(uid, before, after, title="Nickname change", author="someone"):
    return {"title": title, "description": f"**Before:** {before}\n**+After:** {after}",
            "footer": {"text": f"ID: {uid}"}, "author": {"name": author}}

def record(embs, time="2026-09-20T16:36:47.527000+00:00", botm="Dyno", mid=1):
    return {"id": mid, "time": time, "bot": botm, "embeds": embs}


class ParseTests(unittest.TestCase):
    def test_dyno_changed(self):
        got = bot.parse_nick_embed(dyno_emb("487292608448823308", "Old Nick", "New Nick"))
        self.assertEqual(got, ("487292608448823308", "changed", "Old Nick", "New Nick"))

    def test_dyno_cleared_counts_as_removed(self):
        got = bot.parse_nick_embed(dyno_emb("1", "Old", "", action="cleared"))
        self.assertEqual(got[1], "removed")

    def test_carl_change_with_the_plus_decoration(self):
        got = bot.parse_nick_embed(carl_emb("622119328422166528", "jmaster23", "Oingima"))
        self.assertEqual(got, ("622119328422166528", "changed", "jmaster23", "Oingima"))

    def test_carl_added(self):
        got = bot.parse_nick_embed(carl_emb("1", "pixxl_", "Piss Drinker (maybe) Pixxl_", title="Nickname added"))
        self.assertEqual(got[1], "added")

    def test_carl_removed(self):
        got = bot.parse_nick_embed(carl_emb("1", "Old", "", title="Nickname removed"))
        self.assertEqual(got[1], "removed")

    def test_non_nick_embeds_are_rejected(self):
        noise = [
            {"title": "Message edited in #general-chat", "description": "**Before:** a\n**+After:** b",
             "footer": {"text": "ID: 1"}},  #sneaky: same before/after lines, wrong title
            {"title": "Role added", "description": "<@&1>", "footer": {"text": "ID: 1"}},
            {"title": "Avatar update"},
            {"title": "Name change", "description": "**Before:** a\n**+After:** b", "footer": {"text": "ID: 1"}},
            {"description": "**<@1> was given the `Azalea` role**", "footer": {"text": "ID: 1"}},
            {},  #not even an embed really
        ]
        for emb in noise:
            self.assertIsNone(bot.parse_nick_embed(emb), f"{emb} should not parse")

    def test_carl_without_footer_id_is_rejected(self):
        emb = carl_emb("1", "a", "b")
        del emb["footer"]
        self.assertIsNone(bot.parse_nick_embed(emb))


class NicksFromEventTests(unittest.TestCase):
    def test_added_only_keeps_the_after(self):
        #carl's "added" logs the plain username as before — never a real nickname
        self.assertEqual(bot.nicks_from_event("added", "username", "Real Nick"), ["Real Nick"])

    def test_removed_only_keeps_the_before(self):
        self.assertEqual(bot.nicks_from_event("removed", "Old Nick", None), ["Old Nick"])

    def test_changed_keeps_both(self):
        self.assertEqual(bot.nicks_from_event("changed", "A", "B"), ["A", "B"])

    def test_blanks_dropped(self):
        self.assertEqual(bot.nicks_from_event("removed", "", None), [])


class EventsTests(unittest.TestCase):
    def test_both_bots_reporting_one_change_counts_once(self):
        recs = [record([dyno_emb("1", "A", "B")], time="2026-09-20T16:36:47.000000+00:00", botm="Dyno"),
                record([carl_emb("1", "A", "B")], time="2026-09-20T16:36:48.000000+00:00", botm="Carl")]
        events = bot.events_from_records(recs)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["user_id"], "1")

    def test_same_change_months_apart_stays_two_events(self):
        recs = [record([dyno_emb("1", "A", "B")], time="2026-01-01T00:00:00.000000+00:00"),
                record([dyno_emb("1", "A", "B")], time="2026-06-01T00:00:00.000000+00:00")]
        self.assertEqual(len(bot.events_from_records(recs)), 2)

    def test_events_come_out_chronological(self):
        recs = [record([dyno_emb("1", "B", "C")], time="2026-06-01T00:00:00.000000+00:00"),
                record([dyno_emb("1", "A", "B")], time="2026-01-01T00:00:00.000000+00:00")]
        events = bot.events_from_records(recs)
        self.assertEqual([e["after"] for e in events], ["B", "C"])

    def test_both_dialects_of_a_removal_count_as_one_event(self):
        #same nick removal: dyno logs after as the literal "None", carl as the username
        recs = [record([dyno_emb("5", "Old Nick", "None")], time="2026-04-03T04:32:00.000000+00:00"),
                record([carl_emb("5", "Old Nick", "under.heaven.", title="Nickname removed")],
                       time="2026-04-03T04:32:01.000000+00:00", botm="Carl")]
        events = bot.events_from_records(recs)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["before"], "Old Nick")
        self.assertIsNone(events[0]["after"])  #renders as (none), not the word None

    def test_both_dialects_of_a_first_set_count_as_one_event(self):
        #same first nick: dyno logs before as "None", carl as the username
        recs = [record([dyno_emb("5", "None", "Mika")], time="2026-04-03T23:02:00.000000+00:00"),
                record([carl_emb("5", "under.heaven.", "Mika", title="Nickname added")],
                       time="2026-04-03T23:02:01.000000+00:00", botm="Carl")]
        events = bot.events_from_records(recs)
        self.assertEqual(len(events), 1)
        self.assertIsNone(events[0]["before"])


class PrettyDisplayTests(unittest.TestCase):
    #enough of discord.Interaction for the print_nicknames callback: response for
    #page one, followup for the overflow pages
    class FakeInterac:
        class Sink:
            def __init__(self):
                self.sent = []
                self.embeds = []

            async def send_message(self, content=None, **kwargs):
                self.sent.append(content)
                if kwargs.get("embed") is not None:
                    self.embeds.append(kwargs["embed"])

            async def send(self, content=None, **kwargs):
                self.sent.append(content)
                if kwargs.get("embed") is not None:
                    self.embeds.append(kwargs["embed"])

        def __init__(self):
            self.response = self.Sink()
            self.followup = self.Sink()

    def test_dyno_none_fields_are_not_nicknames(self):
        #dyno literally writes "None" in a field when there was no nickname there
        self.assertEqual(bot.nicks_from_event("changed", "None", "Real"), ["Real"])
        self.assertEqual(bot.nicks_from_event("changed", "Real", "None"), ["Real"])
        self.assertEqual(bot.nicks_from_event("removed", "None", None), [])

    def test_chunk_lines_respects_the_cap(self):
        self.assertEqual(bot.chunk_lines([]), [""])
        self.assertEqual(bot.chunk_lines(["a", "b"]), ["a\nb"])
        pages = bot.chunk_lines(["x" * 1000, "y" * 1000, "z"], cap=1900)
        self.assertEqual(len(pages), 2)
        self.assertTrue(all(len(p) <= 1900 for p in pages))

    def test_nick_line_renders_pills_and_pads(self):
        self.assertEqual(bot.nick_line(2, "old", "25-01-01", 1), "`#2` `25-01-01` old")
        self.assertEqual(bot.nick_line(2, "old", None, 2), "`#02` `(undated)` old")

    def test_send_paged_embeds_titles_and_overflow(self):
        interac = self.FakeInterac()
        run = asyncio.run(bot.send_paged_embeds(interac, ["page one", "page two"], "A — 9 nicknames", True))
        self.assertEqual(len(interac.response.embeds), 1)
        self.assertEqual(len(interac.followup.embeds), 1)
        first, second = interac.response.embeds[0], interac.followup.embeds[0]
        self.assertEqual(first.title, "A — 9 nicknames · 1/2")
        self.assertEqual(first.description, "page one")
        self.assertEqual(second.title, "A — 9 nicknames · 2/2")
        self.assertEqual(second.description, "page two")

    def test_send_paged_embeds_single_page_has_no_counter(self):
        interac = self.FakeInterac()
        asyncio.run(bot.send_paged_embeds(interac, ["only"], "A — 3 nicknames", False))
        self.assertEqual(interac.response.embeds[0].title, "A — 3 nicknames")
        self.assertEqual(interac.followup.embeds, [])

    def test_user_nick_rows_orders_undated_then_chronological(self):
        with tempfile.TemporaryDirectory() as tmp:
            daba = db.dbthingy(os.path.join(tmp, "t.db"))
            daba.SetupDB()
            daba.addRecord("Users", db.easy_user_str(1, "a", "A"))
            daba.addRecord("Nicknames", db.easy_nickn_str(1, "new"))      #first insert, latest date
            daba.addRecord("Nicknames", db.easy_nickn_str(1, "mystery"))  #no dump entry at all
            daba.addRecord("Nicknames", db.easy_nickn_str(1, "old"))      #second insert, oldest date
            user = type("U", (), {"id": 1, "display_name": "A"})()
            original = bot.nick_first_seen
            try:
                bot.nick_first_seen = lambda: {("1", "old"): "25-01-01", ("1", "new"): "26-01-01"}
                rows = bot.user_nick_rows(daba, user)
                self.assertEqual([r[1] for r in rows], ["mystery", "old", "new"])
                self.assertEqual([r[2] for r in rows], [None, "25-01-01", "26-01-01"])

                #indexing speaks the same order: #1 is the undated one, #3 the newest
                self.assertEqual(bot.nick_by_index(daba, user, 1)[1], "mystery")
                self.assertEqual(bot.nick_by_index(daba, user, 3)[1], "new")
                self.assertIsNone(bot.nick_by_index(daba, user, 4))
                self.assertIsNone(bot.nick_by_index(daba, user, 0))
            finally:
                bot.nick_first_seen = original
            daba.finish()

    def test_print_nicknames_is_pretty_and_paged(self):
        with tempfile.TemporaryDirectory() as tmp:
            daba = db.dbthingy(os.path.join(tmp, "t.db"))
            daba.SetupDB()
            daba.addRecord("Users", db.easy_user_str(1, "a", "A"))
            daba.addRecord("Nicknames", db.easy_nickn_str(1, "new"))
            daba.addRecord("Nicknames", db.easy_nickn_str(1, "mystery"))
            daba.addRecord("Nicknames", db.easy_nickn_str(1, "old"))
            bot.client.daba = daba  #commands reach the db through tree.client
            original = bot.nick_first_seen
            try:
                bot.nick_first_seen = lambda: {("1", "old"): "25-01-01", ("1", "new"): "26-01-01"}
                interac = self.FakeInterac()
                run = asyncio.run(command("print_nicknames")(interac, type("U", (), {"id": 1, "display_name": "A"})(), True))
                self.assertEqual(len(interac.response.sent), 1)
                page = interac.response.sent[0]
                self.assertIn("3 nicknames", page)
                self.assertIn("#1  (undated)  mystery", page)
                self.assertIn("#2  25-01-01   old", page)
                self.assertIn("#3  26-01-01   new", page)
            finally:
                bot.nick_first_seen = original
            daba.finish()

class DumpRoundtripTests(unittest.TestCase):
    def test_dump_file_loads_back_and_parses(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = bot.dump_filnam
            recs = [record([dyno_emb("1", "A", "B")], mid=123),
                    record([carl_emb("1", "A", "B")], botm="Carl", mid=124)]
            try:
                bot.dump_filnam = lambda cid: os.path.join(tmp, f"dump{cid}.jsonl")
                with open(bot.dump_filnam(5), "w", encoding="utf-8") as f:
                    for rec in recs:
                        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                loaded = bot.load_log_dump(5)
                self.assertEqual(len(bot.events_from_records(loaded)), 1)
            finally:
                bot.dump_filnam = original  #don't poison other tests


if __name__ == "__main__":
    unittest.main()
