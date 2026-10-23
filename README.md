# shadow-pavilion-bot

A Discord bot that tracks server members' nickname changes in an SQLite database, so nothing gets forgotten. Built for a single server: it logs every nickname change automatically, and slash commands let you look up a user's nickname history, attach explanations to specific nicknames, and dump the raw database.

**Status:** early / WIP (v0.8-ish). Core tracking works; error handling is minimal. See [Known issues](#known-issues).

## Setup

1. Install Python 3, then `pip install -U discord.py`
2. Create a bot in the [Discord Developer Portal](https://discord.com/developers/applications) and enable the **Server Members** and **Message Content** privileged intents, then invite it to your server
3. Edit `constants.py`:
   - `BOT_TOKEN` — from the developer portal, Bot page
   - `GUILD_TOKEN` — your server ID (Discord settings → Advanced → Developer Mode, then right-click the server → Copy Server ID)
   - `ROLE` — ID of the Discord role allowed to use the admin commands (enable Developer Mode, then right-click the role → Copy Role ID)
4. Run it: `python bot.py`
5. On ready and gateway resume, the bot fetches the current member roster from Discord and fills in missing users and nicknames. `/firstrun_init` is still available as a manual cached-roster scan.

## Commands

All commands only exist in the configured guild. "Role-gated" = requires the role set in `constants.py`.

| Command | What it does | Role-gated |
|---|---|---|
| `/firstrun_init` | Create tables, backfill all current members | yes |
| `/print_nicknames user private` | List a user's nicknames as `#1..#N` oldest-first with first-seen dates | no |
| `/explain_nickname user index private` | Show one of a user's nicknames (by its `#`number) and its explanation(s) | no |
| `/add_explanation user index explanation` | Attach an explanation to one of a user's nicknames (by its `#`number) | yes |
| `/dump_table` | Send the raw `nicknames.db` file | no |
| `/direct_sql query` | Run arbitrary SQL against the database | yes |

The bot only ever sees nickname changes from its own start date — but Dyno and Carl-bot log every change to a logging channel. A one-time archive of that channel (`logdump_<id>.jsonl`, gitignored) was mined for every past nickname; those are already in the database, and the commands that did the mining were one-shot and have been removed. The dump file still earns its keep though: the database has no timestamps by design, so it's what puts a user's nicknames in chronological order with first-seen dates. The dump is a snapshot, however — nicknames changed after it was taken would never get dated, so the bot also journals every change it sees live into `livenicks.jsonl` (gitignored), and both files are merged for first-seen dates.

The `#numbers` shown by `/print_nicknames` are per-user positions in that chronological list (the database's `nickn_id` is global and stays hidden underneath); `explain_nickname` and `add_explanation` refer to nicknames by that same `#number`. Each nickname appears once per member: reusing an old name keeps its original row, first-seen date and position. Nicknames neither file saw a change for sort last with an `(undated)` marker, in database insertion order; on a fresh clone with neither file, everything shows as undated.

The ready/resume scan uses a fresh API roster rather than the member cache, so a missed live event can be recovered. It records current nicknames without adding a live journal event: seeing a name on reconnect does not tell us when it was set. Names recovered only this way remain `(undated)`. Later live events still get journaled, but only newly observed names get a first-seen date; reusing an undated name leaves it undated and keeps its position. Older journal entries remain readable. If Discord rejects the roster fetch, the bot logs the error and tries again on the next ready/resume.

## Files

- `bot.py` — the bot itself: client, event handlers, slash commands. The entrypoint.
- `constants.py` — all config (token, guild, role) plus the table definitions (`TABLE_GEN`)
- `db.py` — `dbthingy`, a thin sqlite3 wrapper
- `testbot.py` — old scratch version, fully commented out. Ignore it.
- `nicknames.db` — the SQLite database (created on first run, **gitignored**: it holds real member data)
- `livenicks.jsonl` — the bot's own journal of nick changes it saw live, used to date renames from after the log dump was taken (created on first rename, **gitignored**: real member data)

> **Warning:** running `python db.py` directly executes an embedded test that **drops all tables**. Don't.

## Database schema

| Table | Columns |
|---|---|
| `Users` | `user_id` (PK), `username`, `display_name` |
| `Nicknames` | `nickn_id` (PK), `user_id` (FK), `nickname` |
| `Explanations` | `expln_id` (PK), `nickn_id` (FK), `explanation` |

Schema and per-table insert validation (regex) are defined in `constants.py`. Nicknames are recorded automatically on change and reconciled on ready/resume; users are recorded on those scans and on join.

On startup, `SetupDB` consolidates existing duplicate `(user_id, nickname)` rows, keeping the oldest `nickn_id` and moving every attached explanation to it. The migration runs in one transaction and creates a unique index to prevent further duplicates. Nickname inserts use `INSERT OR IGNORE`. The first cleanup can renumber a member's displayed list as duplicates disappear; later reuses do not add entries or shift indexes.

## Known issues

(from the author's notes at the bottom of `bot.py`)

- Little to no error handling — e.g. invalid SQL just errors in the console and the bot never responds
- Commands are visible to people without the role; only execution is blocked
- SQL injection is possible through command parameters
- Actual username changes aren't tracked, only per-server nicknames
- `AUTOPARSE_DEFAULT` / `TITLESHOUT_DEFAULT` in `constants.py` are currently unused
