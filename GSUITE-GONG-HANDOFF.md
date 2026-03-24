# G-Suite + Gong Skills — Cherry-Pick Handoff

## What

Cherry-pick 4 skills + 4 setup skills + 2 shared infrastructure scripts from the TSM-AI repo into this repo (field-eng-skills). These are proven, working skills used daily in the CoreWeave workspace.

## Source Repo

`~/gitstuff/tsm-ai` (clone of `CoreWeave-Sandbox/tsm-ai`)

## Target Repo

This repo: `~/gitstuff/field-eng-skills` (clone of `wandb/field-eng-skills`)

## Skills to Cherry-Pick

### G-Suite (3 skills + 3 setup skills)

| Skill | Source | Scripts | Apps Script | Auth |
|-------|--------|---------|-------------|------|
| `gcalendar` | `.claude/skills/gcalendar/` | `gcalendar_client.py`, `calendars.py`, `events.py`, `setup_auth.py` | `appscript/Code.gs` | Apps Script + Chrome CDP + Okta SSO |
| `gcalendar-setup` | `.claude/skills/gcalendar-setup/SKILL.md` | (SKILL.md only) | - | - |
| `gdocs` | `.claude/skills/gdocs/` | `gdocs_client.py`, `documents.py`, `setup_auth.py` | `appscript/Code.gs` | Apps Script + Chrome CDP + Okta SSO |
| `gdocs-setup` | `.claude/skills/gdocs-setup/SKILL.md` | (SKILL.md only) | - | - |
| `gmail` | `.claude/skills/gmail/` | `gmail_client.py`, `messages.py`, `threads.py`, `labels.py`, `setup_auth.py` | `appscript/Code.gs` | Apps Script + Chrome CDP + Okta SSO |
| `gmail-setup` | `.claude/skills/gmail-setup/SKILL.md` | (SKILL.md only) | - | - |

### Gong (1 skill + 1 setup skill)

| Skill | Source | Scripts | Auth |
|-------|--------|---------|------|
| `gong` | `.claude/skills/gong/` | `gong_client.py`, `calls.py` | Cookie-based + Chrome CDP auto-refresh |
| `gong-setup` | `.claude/skills/gong-setup/SKILL.md` | (SKILL.md only) | - |

### Shared Infrastructure Scripts (2 scripts)

These are in `scripts/` at the TSM-AI repo root. All 4 skills depend on them.

| Script | Purpose |
|--------|---------|
| `scripts/chrome-debug.sh` | Start/stop Chrome with remote debugging on port 9222. Required for all CDP-based auth. |
| `scripts/gmail-cdp-fetch.sh` | Shell wrapper that navigates Chrome to a URL via CDP and returns page content. Used by gcalendar, gdocs, gmail clients. |
| `scripts/gong-cookie-refresh.sh` | Extracts Gong session cookies from Chrome. Used by gong client auto-refresh. |

## How the Auth Works

All 4 skills use the same pattern:

1. **Google Apps Script** deployed as a web app acts as a proxy to Google APIs (Calendar, Docs, Gmail) or Gong's internal API
2. **Chrome debug instance** (port 9222) runs with your Okta session — handles SSO transparently
3. **Python client** calls the Apps Script URL, routing through Chrome via CDP (`gmail-cdp-fetch.sh`)
4. **Credentials** stored in `~/.tsm-ai/.env` as `*_APPSCRIPT_URL` + `*_APPSCRIPT_KEY` pairs (or `GONG_COOKIE`)

W&B uses Okta SSO for Google Workspace, so this pattern should work as-is.

## Cherry-Pick Steps

### 1. Copy Shared Infrastructure

```bash
# From TSM-AI root
cp scripts/chrome-debug.sh ~/gitstuff/field-eng-skills/scripts/
cp scripts/gmail-cdp-fetch.sh ~/gitstuff/field-eng-skills/scripts/
cp scripts/gong-cookie-refresh.sh ~/gitstuff/field-eng-skills/scripts/
chmod +x ~/gitstuff/field-eng-skills/scripts/*.sh
```

### 2. Copy Skills (copy as-is, then adapt)

For each skill, copy the entire directory:

```bash
SRC=~/gitstuff/tsm-ai/.claude/skills
DST=~/gitstuff/field-eng-skills/.claude/skills

# G-Suite
for skill in gcalendar gcalendar-setup gdocs gdocs-setup gmail gmail-setup gong gong-setup; do
  cp -r "$SRC/$skill" "$DST/$skill"
done
```

Then clean up per skill:
- Remove `.venv/`, `__pycache__/`, `.pytest_cache/` (covered by .gitignore)
- Keep `pyproject.toml`, `uv.lock`, `SKILL.md`, `scripts/`, `appscript/`

### 3. Adaptation Needed

These skills were built for the CoreWeave TSM workspace. Adaptations needed for W&B SEs:

**Minimal adaptation (copy as-is):**
- All Python scripts (`*_client.py`, `*.py`) — the client pattern is generic
- All Apps Script (`Code.gs`) — these are Google API wrappers, workspace-agnostic
- All setup skills (`*-setup/SKILL.md`) — credential setup instructions are generic
- `chrome-debug.sh` and `gmail-cdp-fetch.sh` — pure Chrome CDP, no workspace specifics

**May need adaptation:**
- `gong_client.py` — has CoreWeave-specific constants:
  - `workspace_id = 7297253215147980942`
  - `company_id = 4746705030744395723`
  - Base URL: `https://us-54638.app.gong.io`
  - These need to be discovered for W&B's Gong instance (if different from CoreWeave's)
- `gong-cookie-refresh.sh` — may reference CoreWeave-specific Gong domain
- SKILL.md files reference `./scripts/chrome-debug.sh` — verify the relative path still works from field-eng-skills root

**Check but likely fine:**
- `gcalendar_client.py` line 23: `CDP_FETCH_SCRIPT` path traversal (`Path(__file__).parent.parent.parent.parent.parent / 'scripts'`) — verify this resolves correctly from the field-eng-skills directory structure
- Same path traversal in `gdocs_client.py`, `gmail_client.py`

### 4. Update Ecosystem Files

After copying, update these files in field-eng-skills:

**`credential-reference/SKILL.md`** — add:
```
| `GCALENDAR_APPSCRIPT_URL` | Google Calendar | `/gcalendar-setup` |
| `GCALENDAR_APPSCRIPT_KEY` | Google Calendar | `/gcalendar-setup` |
| `GDOCS_APPSCRIPT_URL` | Google Docs | `/gdocs-setup` |
| `GDOCS_APPSCRIPT_KEY` | Google Docs | `/gdocs-setup` |
| `GMAIL_APPSCRIPT_URL` | Gmail | `/gmail-setup` |
| `GMAIL_APPSCRIPT_KEY` | Gmail | `/gmail-setup` |
| `GONG_COOKIE` | Gong | `/gong-setup` |
```

**`credential-status/scripts/check.sh`** — add health checks for each service (follow the existing Salesforce pattern — call a lightweight Python test via the client)

**`skill-composition.md`** — update Communication Prep and Cadence Prep workflows to include gcalendar and gmail as optional data sources

**`CLAUDE.md`** — add skills to project structure, add credential rows

**`README.md`** — add skills to appropriate tables, update Quick Start credentials block, update skill count

### 5. Deploy Apps Scripts

Each SE needs to deploy their own Apps Scripts (one per Google API). The setup skills guide this process:

1. Create a new Google Apps Script project at script.google.com
2. Paste the `Code.gs` content from the skill's `appscript/` directory
3. Deploy as web app (execute as: me, access: anyone with link)
4. Copy the deployment URL and set a secret API key
5. Save URL + key to `~/.tsm-ai/.env`

### 6. Verify

```bash
# Start Chrome debug instance
./scripts/chrome-debug.sh start

# Sign into Okta in the Chrome window that opens

# Test each skill
uv run --project .claude/skills/gcalendar python .claude/skills/gcalendar/scripts/events.py today --pretty
uv run --project .claude/skills/gmail python .claude/skills/gmail/scripts/messages.py search --query "is:unread" --max-results 5 --pretty
uv run --project .claude/skills/gdocs python .claude/skills/gdocs/scripts/documents.py get --id TEST_DOC_ID --pretty
uv run --project .claude/skills/gong python .claude/skills/gong/scripts/calls.py list --limit 5 --pretty
```

## File Inventory

Total files to copy (excluding .venv, __pycache__):

| Directory | Files |
|-----------|-------|
| `scripts/` (repo root) | 3 shell scripts |
| `gcalendar/` | SKILL.md, pyproject.toml, uv.lock, 4 Python scripts, 1 Apps Script |
| `gcalendar-setup/` | SKILL.md |
| `gdocs/` | SKILL.md, pyproject.toml, uv.lock, 3 Python scripts, 1 Apps Script |
| `gdocs-setup/` | SKILL.md |
| `gmail/` | SKILL.md, pyproject.toml, uv.lock, 5 Python scripts, 1 Apps Script |
| `gmail-setup/` | SKILL.md |
| `gong/` | SKILL.md, pyproject.toml, uv.lock, 2 Python scripts |
| `gong-setup/` | SKILL.md |
| **Total** | ~30 files |

## Gong SFDC Cross-Reference

Gong calls sync to Salesforce as `Gong__Gong_Call__c` objects. The `/salesforce` skill in this repo can query these. The Gong SKILL.md documents the SOQL query pattern for finding call IDs by account.

## Notes

- The `setup_auth.py` files in gcalendar, gdocs, gmail are helpers for the Apps Script deployment — they verify connectivity after setup
- Gmail is **read-only** by design (Apps Script only uses read methods)
- GDocs and GCalendar support writes, but all write operations require user confirmation
- Gong is read-only (call recordings, transcripts, AI summaries)
- All skills follow the same `uv run --project` pattern as existing skills in this repo
