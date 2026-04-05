---
name: confluence
description: "Use when reading, creating, or updating Confluence wiki pages or blog posts. Activate for FE space content, personal drafts, meeting notes, runbooks, TCD documents, or delivery tracking pages."
argument-hint: "[get/create/update] [args...]"
allowed-tools: Bash(uv run --project .claude/skills/confluence *)
requires-credentials:
  - ATLASSIAN_EMAIL
  - ATLASSIAN_TOKEN
setup-skill: atlassian-setup
service-url: https://coreweave.atlassian.net/wiki
auto-refresh: false
---

# Confluence API Operations

Interact with the CoreWeave Confluence wiki using Python tools powered by `atlassian-python-api`.

Refer to `.claude/rules/atlassian.md` for shared Atlassian constants.

## Choosing a Space

- **FE space** (default): Use for all team content — meeting notes, runbooks, project pages.
- **Personal space** (`flabat`): Use when the user asks for personal pages or blog posts.

Default to FE unless the user explicitly asks for personal content. Pass `--space personal` to target the personal space.

## Prerequisites

- `ATLASSIAN_EMAIL` and `ATLASSIAN_TOKEN` configured in `~/.fe-skills/.env` (run `/atlassian-setup` if not done)
- Dependencies installed: `cd .claude/skills/confluence && uv sync`

## Tool Invocation

All commands are run from the project root:

```bash
uv run --project .claude/skills/confluence python .claude/skills/confluence/scripts/pages.py <command> [options] [--pretty]
uv run --project .claude/skills/confluence python .claude/skills/confluence/scripts/blogs.py <command> [options] [--pretty]
```

The `--pretty` flag can appear anywhere and produces human-readable JSON output.

## Page Operations — `pages.py`

### Read Operations (Default)

These operations are safe and do not modify any content. Use them freely.

#### Get a page by ID

```bash
uv run --project .claude/skills/confluence python .claude/skills/confluence/scripts/pages.py get --id PAGE_ID --pretty
```

Returns page title, body (HTML storage format), version, space, and URL.

#### Search pages by title

```bash
uv run --project .claude/skills/confluence python .claude/skills/confluence/scripts/pages.py search --title "Meeting Notes" --pretty
uv run --project .claude/skills/confluence python .claude/skills/confluence/scripts/pages.py search --title "Personal Draft" --space personal --pretty
```

#### Search with CQL (Confluence Query Language)

```bash
uv run --project .claude/skills/confluence python .claude/skills/confluence/scripts/pages.py cql --query 'space=FE AND title~"weekly"' --limit 10 --pretty
```

CQL is powerful for complex queries. Common patterns:
- `space=FE AND title~"search terms"` — title contains
- `space=FE AND type=page AND lastModified > now("-7d")` — recently modified
- `space=FE AND label="meeting-notes"` — by label
- `ancestor=PAGE_ID` — all descendants of a page

#### List child pages

Works for both pages and folders. Falls back to CQL when the v1 API returns empty (which happens for folders).

```bash
uv run --project .claude/skills/confluence python .claude/skills/confluence/scripts/pages.py children --id PARENT_PAGE_OR_FOLDER_ID --limit 25 --pretty
```

#### List spaces

```bash
uv run --project .claude/skills/confluence python .claude/skills/confluence/scripts/pages.py spaces --pretty
```

### Write Operations (Require Explicit User Confirmation)

**IMPORTANT: Never execute write operations without explicit user confirmation.** Before running any create, update, or delete command, warn the user what will be changed and get their approval.

#### Create a folder

Create a Confluence folder (container for pages). Uses the v2 API. The FE Customers folder ID is `942965130`.

```bash
uv run --project .claude/skills/confluence python .claude/skills/confluence/scripts/pages.py create-folder --title "Folder Name" --parent-id PARENT_FOLDER_ID --pretty
```

Returns the new folder's `id`, `title`, and `parentId`.

#### Create a page

Ask the user to confirm: page title, parent page/folder, and content summary.

Creates a **Live Doc** by default (real-time collaborative editing, no publish step). Pass `--subtype page` to create a traditional page instead.

```bash
# Live Doc (default)
uv run --project .claude/skills/confluence python .claude/skills/confluence/scripts/pages.py create --title "Page Title" --body "<p>HTML content</p>" --parent-id PARENT_ID --pretty

# Traditional page
uv run --project .claude/skills/confluence python .claude/skills/confluence/scripts/pages.py create --title "Page Title" --body "<p>HTML content</p>" --parent-id PARENT_ID --subtype page --pretty

# Personal space
uv run --project .claude/skills/confluence python .claude/skills/confluence/scripts/pages.py create --title "Personal Page" --body "<p>Content</p>" --space personal --pretty
```

The `--parent-id` can be a page ID or a folder ID.

#### Move a page

Move a page under a new parent (page or folder). Uses the v2 API because the SDK's `move_page` silently fails.

```bash
uv run --project .claude/skills/confluence python .claude/skills/confluence/scripts/pages.py move-page --id PAGE_ID --parent-id NEW_PARENT_ID --pretty
```

#### Update a page

The SDK handles version incrementing automatically — no need to fetch the version first.

```bash
uv run --project .claude/skills/confluence python .claude/skills/confluence/scripts/pages.py update --id PAGE_ID --title "Updated Title" --body "<p>New content</p>" --pretty
uv run --project .claude/skills/confluence python .claude/skills/confluence/scripts/pages.py update --id PAGE_ID --title "Minor Fix" --body "<p>Content</p>" --minor --pretty
```

#### Delete a page

**Warn the user that this is irreversible.**

```bash
uv run --project .claude/skills/confluence python .claude/skills/confluence/scripts/pages.py delete --id PAGE_ID --pretty
```

#### Upload an attachment

```bash
uv run --project .claude/skills/confluence python .claude/skills/confluence/scripts/pages.py attach --id PAGE_ID --file /path/to/file.pdf --pretty
```

#### Manage labels

```bash
uv run --project .claude/skills/confluence python .claude/skills/confluence/scripts/pages.py labels --id PAGE_ID --add label1 label2 --pretty
uv run --project .claude/skills/confluence python .claude/skills/confluence/scripts/pages.py labels --id PAGE_ID --remove old-label --pretty
```

#### Add a comment

```bash
uv run --project .claude/skills/confluence python .claude/skills/confluence/scripts/pages.py comment --id PAGE_ID --body "Comment text" --pretty
```

## Blog Post Operations — `blogs.py`

### Read Operations

#### List blog posts

```bash
uv run --project .claude/skills/confluence python .claude/skills/confluence/scripts/blogs.py list --pretty
uv run --project .claude/skills/confluence python .claude/skills/confluence/scripts/blogs.py list --space personal --limit 5 --pretty
```

#### Get a blog post by ID

```bash
uv run --project .claude/skills/confluence python .claude/skills/confluence/scripts/blogs.py get --id BLOG_ID --pretty
```

### Write Operations (Require Explicit User Confirmation)

#### Create a blog post

```bash
uv run --project .claude/skills/confluence python .claude/skills/confluence/scripts/blogs.py create --title "Post Title" --body "<p>Content</p>" --pretty
uv run --project .claude/skills/confluence python .claude/skills/confluence/scripts/blogs.py create --title "Personal Post" --body "<p>Content</p>" --space personal --pretty
```

#### Update a blog post

```bash
uv run --project .claude/skills/confluence python .claude/skills/confluence/scripts/blogs.py update --id BLOG_ID --title "Updated Title" --body "<p>New content</p>" --pretty
```

#### Delete a blog post

**Warn the user that this is irreversible.**

```bash
uv run --project .claude/skills/confluence python .claude/skills/confluence/scripts/blogs.py delete --id BLOG_ID --pretty
```

## Common HTML Storage Patterns

When creating or updating content, use Confluence storage format (XHTML):

| Element | Storage Format |
|---|---|
| Heading | `<h1>Title</h1>` |
| Paragraph | `<p>Text</p>` |
| Bold | `<strong>text</strong>` |
| Code block | `<ac:structured-macro ac:name="code"><ac:plain-text-body><![CDATA[code here]]></ac:plain-text-body></ac:structured-macro>` |
| Info panel | `<ac:structured-macro ac:name="info"><ac:rich-text-body><p>text</p></ac:rich-text-body></ac:structured-macro>` |
| Table | `<table><tbody><tr><th>Header</th></tr><tr><td>Cell</td></tr></tbody></table>` |
| Link | `<a href="https://example.com">text</a>` |
| Page link | `<ac:link><ri:page ri:content-title="Page Title" /></ac:link>` |

## Error Handling

All tools output structured JSON. On success, results go to stdout. On error, a JSON object with `ok`, `error`, and `message` fields goes to stderr, and the process exits with code 1.

Common errors:
- `credentials_not_found` — `ATLASSIAN_EMAIL`/`ATLASSIAN_TOKEN` missing from `~/.fe-skills/.env`; run `/atlassian-setup`
- `credentials_missing` — `ATLASSIAN_EMAIL` or `ATLASSIAN_TOKEN` not set in `~/.fe-skills/.env`
- `api_error` with "Authentication failed" — bad credentials
- `api_error` with "Permission denied" — no access to space/page
- `api_error` with "Not found" — invalid page ID
- `api_error` with "Version conflict" — stale version; re-fetch the page

## Related Skills

- `/jira` — Linked Jira issues, epics, and customer work items
- `/slack` — Thread context and conversation references for wiki content
- `/salesforce` — Account data and commercial details for customer pages

## Safety Rules

- **Default to read-only.** All read operations (search, list, get) can be executed without asking.
- **Never write without confirmation.** Create, update, delete, attach, label, and comment operations must be explicitly approved by the user before execution.
- **Show what will change.** Before a write operation, display the title, target page, and a summary of the content being written.
- **Prefer the least destructive option.** Update rather than delete-and-recreate.
