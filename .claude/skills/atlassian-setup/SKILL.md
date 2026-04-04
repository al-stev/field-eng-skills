---
name: atlassian-setup
description: "One-time Atlassian API token setup for Jira and Confluence. Run before first use of /jira or /confluence, when ATLASSIAN_TOKEN is missing, or on 'set up Jira/Confluence'."
disable-model-invocation: true
allowed-tools: Bash(brew *), Bash(jira *), Bash(chmod *), Bash(uv run --project .claude/skills/confluence python .claude/skills/confluence/scripts/*.py *)
---

# Atlassian Setup

One-time setup for Atlassian tooling used by W&B SE skills (Jira, Confluence).

## Instances

| Service | Instance | Used for |
|---|---|---|
| Jira | `coreweave.atlassian.net` | Customer bugs, feature requests, escalations (WB project) |
| Confluence | `coreweave.atlassian.net` | Internal documentation, knowledge base |

Both instances use the same API token (tied to your Atlassian ID).

## Prerequisites

- Homebrew installed
- An Atlassian account with access to both instances

## Step 1: Generate an Atlassian API Token

1. Open: https://id.atlassian.com/manage-profile/security/api-tokens
2. Click **Create API token**
3. Label it something like `claude-code` or `wandb-se`
4. Copy the token — you will need it in the next step

## Step 2: Save Credentials to `~/.fe-skills/.env`

Ensure the credential directory exists:

```bash
mkdir -p ~/.fe-skills && chmod 700 ~/.fe-skills
```

Use the **Edit tool** to append credentials to `~/.fe-skills/.env`:
- Add two lines:
  ```
  ATLASSIAN_EMAIL=your-email@coreweave.com
  ATLASSIAN_TOKEN=your-api-token
  ```
- Replace the placeholder values with your actual email and API token from Step 1
- Do **NOT** use `echo`, `printf`, `cat >>`, or any bash command to write credentials — these leak into shell history

Then lock file permissions:

```bash
chmod 600 ~/.fe-skills/.env
```

## Step 3: Install Jira CLI (Optional)

> **Note:** The Python Jira skill (`/jira`) no longer requires `jira-cli`. Steps 3-4 are only needed if you want the `jira` CLI for ad-hoc terminal use.

```bash
brew install ankitpokhrel/jira-cli/jira-cli
```

## Step 4: Configure Jira CLI (Optional)

Run the interactive setup:

```bash
jira init
```

When prompted, use these values:

| Prompt | Value |
|---|---|
| Installation type | **Cloud** |
| Link | `https://coreweave.atlassian.net` |
| Login type | Choose the option that uses API token |
| Project | `WB` |
| Board | (select the appropriate WB board) |

## Step 5: Verify Everything Works

### Jira (W&B instance)

```bash
jira me
```

Should print your Atlassian user profile.

### Confluence (CoreWeave instance)

```bash
uv run --project .claude/skills/confluence python .claude/skills/confluence/scripts/pages.py spaces --pretty
```

Should return JSON with accessible Confluence spaces. No credentials appear in the command — Python reads them from `~/.fe-skills/.env` internally.

## Troubleshooting

### Jira CLI debug mode

```bash
jira issue list --debug
```

### Reset Jira CLI configuration

```bash
rm ~/.config/.jira/.config.yml
jira init
```

### Common issues

- **401 Unauthorized**: Check that `ATLASSIAN_EMAIL` and `ATLASSIAN_TOKEN` in `~/.fe-skills/.env` have the correct values, and that file permissions are `600`.
- **Confluence API returns HTML instead of JSON**: Make sure the URL includes `/wiki/api/v2/` — missing `/wiki` is the most common mistake.
- **Wrong Jira instance**: Both W&B Jira and CoreWeave Confluence are now at `coreweave.atlassian.net`. The previous W&B-specific instance was migrated to CoreWeave in Phase 7.
