# shadow-pavilion-bot

A Discord bot that tracks server members' nickname changes in an SQLite database, so nothing gets forgotten. Built for a single server: it logs every nickname change automatically, and slash commands let you look up a user's nickname history, attach explanations to specific nicknames, and dump the raw database.

**Status:** early / WIP (v0.8-ish). Core tracking works; error handling is minimal. See [Known issues](#known-issues).

## Setup

1. Install Python 3, then `pip install -U discord.py`
2. Create a bot in the [Discord Developer Portal](https://discord.com/developers/applications) and enable the **Server Members** and **Message Content** privileged intents, then invite it to your server
3. Edit `constants.py`:
   - `BOT_TOKEN` — from the developer portal, Bot page
   - `GUILD_TOKEN` — your server ID (Discord settings → Advanced → Developer Mode, then right-click the server → Copy Server ID)
   - `ROLE` — name of the Discord role allowed to use the admin commands
4. Run it: `python bot.py`
5. In Discord, someone with that role runs `/firstrun_init` once — creates the tables and backfills all current members

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
| `/download_logs [channel]` | Dump a channel's entire history to `logdump_<id>.jsonl` (defaults to the configured logging channel) | yes |
| `/backfill_nicknames [channel]` | Parse the dump's Dyno/Carl-bot nickname logs into the database as past nicknames | yes |
| `/nickname_history user private` | Print a user's nickname changes in chronological order from the dump | no |

The bot only ever sees nickname changes from its own start date — but Dyno and Carl-bot log every change to a logging channel. `/download_logs` archives that channel (the Message Content intent is required for this), `/backfill_nicknames` recovers every old nickname out of it into the database, and `/nickname_history` shows the timeline (the database has no timestamps by design, so order comes from the dump).

The `#numbers` shown by `/print_nicknames` are per-user positions in that chronological list (the database's `nickn_id` is global and stays hidden underneath); `explain_nickname` and `add_explanation` refer to nicknames by that same `#number`. Nicknames the log dump never saw a change for sort first with an `(undated)` marker.

## Files

- `bot.py` — the bot itself: client, event handlers, slash commands. The entrypoint.
- `constants.py` — all config (token, guild, role) plus the table definitions (`TABLE_GEN`)
- `db.py` — `dbthingy`, a thin sqlite3 wrapper
- `testbot.py` — old scratch version, fully commented out. Ignore it.
- `nicknames.db` — the SQLite database

> **Warning:** running `python db.py` directly executes an embedded test that **drops all tables**. Don't.

## Database schema

| Table | Columns |
|---|---|
| `Users` | `user_id` (PK), `username`, `display_name` |
| `Nicknames` | `nickn_id` (PK), `user_id` (FK), `nickname` |
| `Explanations` | `expln_id` (PK), `nickn_id` (FK), `explanation` |

Schema and per-table insert validation (regex) are defined in `constants.py`. Nicknames are recorded automatically on change; users are recorded on first run and on join.

## Known issues

(from the author's notes at the bottom of `bot.py`)

- Little to no error handling — e.g. invalid SQL just errors in the console and the bot never responds
- Commands are visible to people without the role; only execution is blocked
- SQL injection is possible through command parameters
- Actual username changes aren't tracked, only per-server nicknames
- `AUTOPARSE_DEFAULT` / `TITLESHOUT_DEFAULT` in `constants.py` are currently unused
