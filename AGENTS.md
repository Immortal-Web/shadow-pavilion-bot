# AGENTS.md

Guidance for AI coding agents working in this repo.

## Repository workflow

This is a fork: `origin` = Immortal-Web/shadow-pavilion-bot, `upstream` = dracOS-01-1/shadow-pavilion-bot. Upstream is read-only — never push to it. Contribute by committing to a branch on the fork and opening a PR against upstream.

## What this is

A single-guild Discord bot (discord.py, `app_commands` slash commands) that logs member nickname changes to SQLite. Deliberately tiny: the only external dependency is `discord.py`, everything else is stdlib (`sqlite3`, `re`). Keep it that way — the author explicitly rejected ORMs (SQLAlchemy); plain string SQL is the house style.

## Files

- `bot.py` — the only entrypoint (`python bot.py`). Client subclass, event handlers, all slash commands. The author's own known-issues list lives at the bottom of this file — read it before "fixing" anything; the issues are known and deprioritized.
- `constants.py` — all config (`BOT_TOKEN`, `GUILD_TOKEN`, `ROLE`, `DB_FILENAM`) **and** the table definitions: `TABLE_GEN` = list of `[name, CREATE TABLE sql, insert-values regex]`.
- `db.py` — `dbthingy`, a thin sqlite3 wrapper. Builds SQL via `str.format`; `addRecord` validates values against each table's regex from `TABLE_GEN` — that regex is the only insert validation.
- `testbot.py` — dead scratch copy of an earlier version (entire file inside a triple-quoted string). Do not treat it as source of truth and do not sync changes into it.
- `nicknames.db` — live data file with real member data (ids, names, nicknames). **Gitignored — never commit it** (it was scrubbed from history with a rewrite for exactly that reason). Never delete or overwrite it as part of a change.
- `livenicks.jsonl` — the bot's journal of nick changes it saw live (appended by `on_member_update`); what dates renames from after the log dump was taken. **Gitignored — real member data, never commit it.**

## Hard rules

- **Never run `python db.py`** — its `__main__` block DROPs all three tables. Data loss.
- Never put a real `BOT_TOKEN` in `constants.py`; the file is committed, so it currently holds a placeholder only.
- Never commit `nicknames.db`, `logdump_*.jsonl` or `livenicks.jsonl` — real member data. All are gitignored; keep it that way.
- `testbot.py` is inert; don't "fix" or run it.
- No `requirements.txt` exists. If dependency info is ever needed, the sole external dep is `discord.py`.

## Conventions

- Adding a table = new CREATE sql + insert-values regex + `TABLE_GEN` entry in `constants.py`, plus an `easy_*_str` helper in `db.py` to build the values string.
- Slash commands sync to one guild (`constants.GUILD_TOKEN`); role gating via `@app_commands.checks.has_role(constants.ROLE)`.
- Match the existing code style: plain functions, `str.format` SQL, short helper names. Casual, commented-out-loud comments are the norm in this codebase — don't reformat or "clean up" working code as a side effect.
