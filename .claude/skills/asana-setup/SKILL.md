---
name: asana-setup
description: "One-time Asana PAT setup. Run before first use of /asana, when ASANA_TOKEN is missing or expired, or on 'set up Asana' or 'configure Asana'."
disable-model-invocation: true
allowed-tools: Bash(chmod *), Bash(uv run --project .claude/skills/asana python .claude/skills/asana/scripts/*.py *)
---

# Asana Setup

One-time setup for Asana API access used by the `/asana` skill.

## Prerequisites

- An Asana account (free plan works for basic functionality; Starter plan recommended for full features)
- Signed in to Asana in your browser

## Asana Plan Note

For full functionality (Priority custom field on tasks), **Asana Starter plan** ($10.99/user/month) is recommended. The skill works on the free plan with priority stored in task names as a `[P0]` prefix fallback. Core features (projects, tasks, sections, assignees, due dates) all work on the free plan.

## Step 1: Generate a Personal Access Token (PAT)

1. Open https://app.asana.com/0/my-apps in your browser
2. Click **Create new token**
3. Enter a description (e.g., `claude-code`)
4. Click **Create token**
5. **Copy the token immediately** -- it is only shown once

## Step 2: Save Credentials

Ensure the credential directory exists:

```bash
mkdir -p ~/.fe-skills && chmod 700 ~/.fe-skills
```

Use the **Edit tool** to append the token to `~/.fe-skills/.env`:
- Add a line: `ASANA_TOKEN=<paste-token-here>`
- Do **NOT** use `echo`, `printf`, or any bash command to write credentials -- these leak into shell history

Then lock file permissions:

```bash
chmod 600 ~/.fe-skills/.env
```

## Step 2.5: Auto-discover Workspace GID

After saving the PAT, discover your workspace GID by running:

```bash
uv run --project .claude/skills/asana python -c "
import sys
sys.path.insert(0, '.claude/skills/asana/scripts')
from asana_client import get_client
import asana
client = get_client()
users_api = asana.UsersApi(client)
me = users_api.get_user('me', {'opt_fields': 'gid,name,email,workspaces.gid,workspaces.name'})
print(f'User: {me[\"name\"]} ({me.get(\"email\", \"\")})')
for ws in me.get('workspaces', []):
    print(f'  Workspace: {ws[\"name\"]} (GID: {ws[\"gid\"]})')
"
```

Then update the workspace GID in two places:
1. **`.claude/skills/asana/scripts/asana_client.py`**: Change `_ASANA_WORKSPACE_GID_DEFAULT` from `"REPLACE_AFTER_SETUP"` to your workspace GID
2. **`.claude/rules/asana.md`**: Update the Workspace GID entry

If you have multiple workspaces, choose the one you want to use for SE action tracking.

## Step 3: Install Python Dependencies

```bash
cd .claude/skills/asana && uv sync
```

## Step 4: Verify

Test connectivity by listing projects:

```bash
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/query.py projects --limit 3 --pretty
```

Should return JSON with project entries from your workspace (or an empty list for a new workspace). If you see an auth error, double-check the token in `~/.fe-skills/.env`.

## Step 5: Create SE Team Project (Optional but Recommended)

Create the shared SE Team project for internal/cross-cutting work:

```bash
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/mutate.py setup-project --name "SE Team" --pretty
```

Record the returned `project_gid` in `.claude/rules/asana.md` under the SE Team project GID entry.

## Token Renewal

Asana PATs do not expire automatically. They remain valid until you revoke them. If a token stops working:

1. Go to https://app.asana.com/0/my-apps
2. Revoke the old token
3. Create a new one and update `ASANA_TOKEN` in `~/.fe-skills/.env`

## Troubleshooting

### Authentication failed / 401 errors

- Verify `ASANA_TOKEN` in `~/.fe-skills/.env` has no trailing whitespace
- Make sure you copied the full token
- The PAT may have been revoked -- generate a new one

### 403 Forbidden

- Your Asana account may not have access to the workspace
- Check that you are a member of the workspace

### ModuleNotFoundError

- Run `cd .claude/skills/asana && uv sync` to install Python dependencies.

### Workspace GID errors

- Run the auto-discover command in Step 2.5 to find your workspace GID
- Make sure `_ASANA_WORKSPACE_GID_DEFAULT` in `asana_client.py` is updated
