#whatever I don't care anymore it's been to long I'm not gonna bother doing this properly
#nicknames tracker because I consider that actually important rather than the announcer which is cool admitedtly
#but I couldn't be bothered figuring out. do it yourself if you want


#okay imma be real I just followed along a tutorial for half of this crap
#don't get me started on APIs
import json
import os
import re
import sqlite3
from datetime import datetime

import discord
from discord import app_commands
import constants
import db

#python is so annoying man I hate self.<> sooooo much 


#reference because it's a bit confusing:
'''
-member.name : actual discord username. unique, changeable.
-member.global_name : your regular name. not unique, changeable. what you see in dms.
-member.nick : server specific name. not unique, changeable.
'''
class botman(discord.Client): 
    #autodetect:bool
    #shouting:bool

    daba:db.dbthingy

    def firstRun_setup(self):
        #sets up database
        #if we're re-running this, close the old connection instead of leaking it
        #(an abandoned sqlite handle also locks the db file on windows, which is rude)
        if hasattr(self, "daba"):
            self.daba.finish()
        self.daba = db.dbthingy(db.DB_FILENAM)
        self.daba.SetupDB()
        #also the db thing is like not done properly at all
        #I don't care sqlalchemy is awful I had to use if for work its really really annoying

        #adds all server members to database. might? take a while?
        #ignoredupes so running this twice doesn't die on the primary key,
        #commit=False because one commit at the end beats ten thousand of them
        for member in self.get_guild(constants.GUILD_TOKEN).members:
            self.daba.addRecord("Users",db.easy_user_str(member.id,member.name,member.global_name),ignoredupes=True,commit=False)
            #also grab everyone's current nickname while we're at it
            #(skip the nickless — easy_nickn_str would happily store the word 'None')
            if member.nick is not None:
                self.daba.addRecord("Nicknames",db.easy_nickn_str(member.id,member.nick),ignoredupes=True,commit=False)
        #}
        self.daba.save()
    #}

    #runs exactly once per process, before on_ready (which fires on every reconnect —
    #old code opened a fresh sqlite connection and re-synced commands each time. oops)
    async def setup_hook(self):
        self.daba = db.dbthingy(db.DB_FILENAM)
        self.daba.SetupDB() #if-not-exists, safe every boot

        #you have to like sync it otherwise testing gets annoying cus it takes too long
        #but this limits it to 1 server? ah well whatever
        await tree.sync(guild=discord.Object(id=constants.GUILD_TOKEN))
            #what is tree? good question I dunno.

    #don't even get me started on async but this is basically when the bot actually loads ready
    async def on_ready(self):
       # self.autoparsing= constants.AUTOPARSE_DEFAULT
        #self.titleshouting=constants.TITLESHOUT_DEFAULT

        #everything real moved to setup_hook, this is just a heartbeat now
        print("longged on")
    #}

    async def on_member_join(self,member):
        #we are, in fact, going to scan every person that joins this server
        #ignoredupes: if they left and came back the row's already there, nothing new to learn
        self.daba.addRecord("Users",db.easy_user_str(member.id,member.name,member.global_name),ignoredupes=True)
    #}

    #async def on_message(self, message:discord.Message):
        #scans every message written, sees if author has posted in < {timefraction},
        #if not yells out "hello mr authorname" or whatever

        #this is really stupid though scanning every single message is incredibly dumb
        #maybe there's a different function that lets me do it better but I don't remember finding one
    #}

    async def on_member_update(self, before:discord.Member, after:discord.Member):
        #incredibly convenient function that is literally exactly what I need
        if after.nick != before.nick and after.nick is not None:
            #nick removal isn't a *new* nickname so there's nothing to log (before.nick already had it)
            self.daba.addRecord("Nicknames",db.easy_nickn_str(after.id,after.nick))
            print("nickname change detected, added to db")
        if after.name != before.name or after.global_name != before.global_name:
            #username/display name changes: Users is current-state, so just overwrite
            self.daba.updRecord("Users",
                "username=" + db.sqlstr(after.name) + ", display_name=" + db.sqlstr(after.global_name),
                "user_id = " + db.sqlstr(str(after.id)))
            print("username/display name change detected, updated db")
        #we don't care if someone changed their profile pic or whatever  

    #}
#}

#still not sure what this all is
intents = discord.Intents.default()
#members: needed for join/nick-change events. message_content: nothing reads messages
#off discord anymore (the embed-mining commands got cut), but upstream runs with it
#on, so it stays on here too
intents.members=True
intents.message_content=True

client = botman(intents=intents)
tree = app_commands.CommandTree(client)


#--- digging old nicknames out of the logging channel ---
#dyno and carl-bot both log every nick change to one channel. this bot only ever sees
#changes since it started running, but those two have been logging forever. the mining
#commands that downloaded the channel and poured the old nicknames into the db were a
#one-time job and got cut again once it was done — what's left here is the reading
#half: the dump file they left behind still says when each nickname first showed up,
#and that's what print_nicknames numbers and sorts everybody by

#the dump file, kept next to the db. no command makes it anymore, it just gets carried
#around from the mining days — gitignored (unlike the db, which is the real data)
def dump_filnam(channel_id:int)->str:
    return "logdump_" + str(channel_id) + ".jsonl"

#one embed -> (user_id, kind, before, after), or None if it isn't a nickname event.
#dyno: no title, desc "**<@123> nickname changed**", values as Before/After fields.
#carl: title "Nickname change/added/removed", values as "**Before:** x" "**+After:** y" lines.
#both stick "ID: <user id>" in the footer
def parse_nick_embed(emb:dict):
    desc = emb.get("description") or ""
    fields = {f.get("name","").lower(): f.get("value","").strip() for f in emb.get("fields",[])}

    #dyno. "cleared" is dyno's word for removed, unify them. "change" (carl) -> "changed" too
    dyno = re.search(r"<@(\d+)> nickname (changed|added|removed|cleared)", desc)
    if dyno:
        kind = {"change":"changed","cleared":"removed"}.get(dyno.group(2), dyno.group(2))
        return dyno.group(1), kind, fields.get("before"), fields.get("after")

    if re.fullmatch(r"Nickname (change|added|removed)", (emb.get("title") or "").strip()):
        uid = re.search(r"ID:\s*(\d+)", emb.get("footer",{}).get("text",""))
        if uid is None:
            return None #no id in the footer, no entry (better than guessing who)
        #the + in carl's "**+After:**" is diff-highlight decoration, not part of the name
        before = re.search(r"\*\*Before:\*\*\s*(.*)", desc)
        after = re.search(r"\*\*\+?After:\*\*\s*(.*)", desc)
        kind = "changed" if "change" in emb["title"].lower() else emb["title"].strip().split()[-1].lower()
        return uid.group(1), kind, before.group(1).strip() if before else None, after.group(1).strip() if after else None

    return None #message edits, role changes, avatar updates etc — not ours

#which side(s) of an event were actual nicknames. carl's "added" logs the person's plain
#username as Before — that was never a nickname, so it doesn't go in the nicknames table.
#"None" gets filtered too: dyno literally writes the word None in the Before/after field
#when there wasn't one (first nick / nick cleared), and it is not a nickname either
def nicks_from_event(kind:str, before, after)->list:
    nicks = [after] if kind == "added" else [before] if kind == "removed" else [before, after]
    return [n for n in nicks if n and n != "None"]

#records = the dump file's lines. both bots report the same
#change about a second apart, so identical user+before+after within a minute counts once.
#sorted by time either way, so the timeline comes out chronological
def events_from_records(records:list)->list:
    evs = []
    for rec in records:
        for emb in rec.get("embeds",[]):
            parsed = parse_nick_embed(emb)
            if parsed is None:
                continue
            uid, kind, before, after = parsed
            #make both bots' copies of an event look identical so the dedupe below can
            #spot them as the same change: dyno writes the literal word None where a
            #nick was missing, carl writes the plain username on added/removed events —
            #neither of those is a nickname, so both become a real None here
            before = None if kind == "added" or before == "None" else before
            after = None if kind == "removed" or after == "None" else after
            evs.append({"user_id":uid, "kind":kind, "before":before, "after":after,
                        "time":rec["time"], "bot":rec.get("bot",""),
                        "name":(emb.get("author") or {}).get("name")})
    evs.sort(key=lambda ev: ev["time"])
    last_seen = {}
    events = []
    for ev in evs:
        key = (ev["user_id"], ev["before"], ev["after"])
        when = datetime.fromisoformat(ev["time"])
        if key in last_seen and (when - last_seen[key]).total_seconds() < 60:
            continue #the other bot's copy of the same change
        last_seen[key] = when
        events.append(ev)
    return events

def load_log_dump(channel_id:int)->list:
    with open(dump_filnam(channel_id), encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


#--- showing a user's nicknames in a way a human can read ---
#the db's nickn_id is global (1, 2, ... 421 across everyone) so per-user it looks like
#4, 5, 143, 417 — meaningless. what people see instead: their nicknames numbered #1..#N
#in chronological order. the db has no timestamps (upstream shape), so first-seen dates
#come from the log dump; the ids stay put underneath and only the display is renumbered

#first time each (user_id, nickname) shows up in the log dump -> local 'YYYY-MM-DD'.
#parsed once per dump-file version and cached — the dump is 40k messages, nobody wants
#that re-parsed on every /print_nicknames
_nick_times = {"mtime": None, "map": {}}
def nick_first_seen()->dict:
    try:
        mtime = os.path.getmtime(dump_filnam(constants.LOG_CHANNEL))
    except OSError:
        return {} #no dump: everything is undated, ordering falls back to plain ids
    if _nick_times["mtime"] == mtime:
        return _nick_times["map"]
    seen = {}
    for ev in events_from_records(load_log_dump(constants.LOG_CHANNEL)):
        for nick in nicks_from_event(ev["kind"], ev["before"], ev["after"]):
            seen.setdefault((ev["user_id"], nick), ev["time"])
    _nick_times["mtime"] = mtime
    _nick_times["map"] = {key: datetime.fromisoformat(t).astimezone().strftime("%y-%m-%d")
                          for key, t in seen.items()}
    return _nick_times["map"]

#one user's nicknames as [(nickn_id, nickname, first_seen_or_None)], oldest first.
#undated rows go first — no log event means the nick predates the logging (or nobody
#logged it), which is as good as "old" as we can tell
def user_nick_rows(daba:db.dbthingy, user)->list:
    rows = daba.rdRecords("Nicknames","nickn_id,nickname",f"WHERE user_id = {user.id}")
    seen = nick_first_seen()
    uid = str(user.id)
    dated = sorted(((nid, nick, seen[(uid, nick)]) for nid, nick in rows if (uid, nick) in seen),
                   key=lambda r: (r[2], r[0]))
    undated = [(nid, nick, None) for nid, nick in rows if (uid, nick) not in seen]
    return undated + dated

#turns a "#number from print_nicknames" back into a real row (or None if out of range)
def nick_by_index(daba:db.dbthingy, user, index:int):
    rows = user_nick_rows(daba, user)
    return rows[index-1] if 1 <= index <= len(rows) else None

#discord caps a message at 2000 chars and dedicated nick hoarders blow past it,
#so split the lines into pages and send them one after another
def chunk_lines(lines:list, cap=1900)->list:
    pages, cur, size = [], [], 0
    for line in lines:
        if cur and size + len(line) + 1 > cap:
            pages.append("\n".join(cur))
            cur, size = [], 0
        cur.append(line)
        size += len(line) + 1
    if cur:
        pages.append("\n".join(cur))
    return pages or [""]

async def send_paged(interac:discord.Interaction, pages:list, ephemeral:bool):
    for i, page in enumerate(pages):
        if i == 0:
            await interac.response.send_message(page, ephemeral=ephemeral)
        else:
            await interac.followup.send(page, ephemeral=ephemeral)


#call firstrun
@tree.command(name="firstrun_init",description="initializes everything for setup",guild=discord.Object(id=constants.GUILD_TOKEN))
@app_commands.checks.has_role(constants.ROLE)
async def slashgetall(interac:discord.Interaction):
    tree.client.firstRun_setup()
    await interac.response.send_message("setup complete?")
#}

#dump entire table
@tree.command(name="dump_table", description="spits out raw sql file",guild=discord.Object(id=constants.GUILD_TOKEN))
@app_commands.checks.has_role(constants.ROLE)
async def slashdumptable(interac:discord.Interaction):
    table = discord.File(constants.DB_FILENAM,filename="nicknames.db")
    await interac.response.send_message("file",file=table,ephemeral=True)
#}

#grab nicknames (and ids) of a user
@tree.command(name="print_nicknames",description="prints all of a user's nicknames, numbered #1..#N oldest first",guild=discord.Object(id=constants.GUILD_TOKEN))
async def slashgetnicks(interac:discord.Interaction, user:discord.Member, private:bool):
    rows = user_nick_rows(tree.client.daba, user)
    if not rows:
        await interac.response.send_message(f"{user.display_name} has no nicknames on record", ephemeral=private)
        return
    #the #number is the per-user index — that's what explain/add_explanation want now
    lines = [f"#{i}  {date or '(undated)':<10} {nick}" for i, (_, nick, date) in enumerate(rows, start=1)]
    header = f"{user.display_name} — {len(rows)} nicknames:"
    await send_paged(interac, chunk_lines([header, *lines]), ephemeral=private)
#}

#grab a nickname, and its explanation
@tree.command(name="explain_nickname",description="explains one of a user's nicknames (by its #number from print_nicknames)",guild=discord.Object(id=constants.GUILD_TOKEN))
async def slashexplnnick(interac:discord.Interaction, user:discord.Member, index:int, private:bool):
    #a sensible person would have just done a join but my design is too fragile for that
    row = nick_by_index(tree.client.daba, user, index)
    if row is None:
        await interac.response.send_message(f"#{index}? {user.display_name} doesn't have that many nicknames — check /print_nicknames", ephemeral=private)
        return
    nickn_id, nick, date = row
    expls = tree.client.daba.rdRecords("Explanations","explanation",f"WHERE nickn_id = {nickn_id}")
    msg = f"#{index} — {nick}" + (f" ({date})" if date else "")
    if expls:
        msg += "\n" + "\n".join(f"• {e}" for e, in expls)
    else:
        msg += "\nno explanations yet"
    await interac.response.send_message(msg[:1900], ephemeral=private)
#}

#add explanation using the per-user #number
@tree.command(name="add_explanation",description="add an explanation for one of a user's nicknames (by its #number from print_nicknames)",guild=discord.Object(id=constants.GUILD_TOKEN))
@app_commands.checks.has_role(constants.ROLE)
async def slashaddexpl(interac:discord.Interaction, user:discord.Member, index:int, explanation:str):
    row = nick_by_index(tree.client.daba, user, index)
    if row is None:
        await interac.response.send_message(f"#{index}? {user.display_name} doesn't have that many nicknames — check /print_nicknames", ephemeral=True)
        return
    nickn_id, nick, _ = row
    try:
        succed = tree.client.daba.addRecord("Explanations",db.easy_expln_str(nickn_id,explanation))
    except sqlite3.Error as e:
        #typo'd nickn_id trips the foreign key. used to escape and discord would show "did not respond"
        await interac.response.send_message("failed to add (bad characters? blank?)",ephemeral=True)
        return
    if succed:
        await interac.response.send_message(f"explanation added to #{index} '{nick}'",ephemeral=True)
    else:
        #basically only fails on weird characters now (apostrophes work), but don't lie about it
        await interac.response.send_message("failed to add (bad characters? blank?)",ephemeral=True)
#}

#update explanation using id
    #can't be bothered whatever just don't make mistakes lol

#emergency direct SQL
@tree.command(name="direct_sql",description="directly performs sql",guild=discord.Object(id=constants.GUILD_TOKEN))
@app_commands.checks.has_role(constants.ROLE)
async def slashemergsql(interac:discord.Interaction,query:str):
    try:
        result = tree.client.daba.raw(query)
    except sqlite3.Error as e:
        #used to just die here and the discord client would show "did not respond". not anymore
        await interac.response.send_message(f"sql error: {e}",ephemeral=True)
        return

    role = discord.utils.get(interac.guild.roles, name=constants.ROLE)
    mention = role.mention if role else "@" + constants.ROLE

    if result is None:
        result = "done. no rows."
    #discord caps messages at 2000 chars so butcher anything enormous before it bites us
    msg = f"{mention} raw executed. query: {query}\n{str(result)}"
    await interac.response.send_message(msg[:1900])
#}



if __name__ == '__main__':
    #so tests can import this file without trying to log into discord with a fake token
    client.run(constants.BOT_TOKEN)

#current issues I can't be bothered to address:
'''
-ux is a bit bad
    (responses and whatever)
-error messages? never heard of that
    -if you do bad sql or something it wont damage anyhing but youll just get an erro in the command line and no response from the bot
-if you don't have the role you can still see the commands for some reason
-you can probably do sql injection but whatever
-notice when someone changes their actual username and not just their nicknames
-
'''
