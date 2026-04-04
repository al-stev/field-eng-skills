# Slack Write Operations Reference

Write operations (posting messages, adding reactions) are not yet implemented in the Python tools. Use these curl fallbacks.

## Post a message

```bash
curl -s "https://slack.com/api/chat.postMessage" -H "Authorization: Bearer $(grep '^SLACK_TOKEN=' ~/.fe-skills/.env | cut -d= -f2-)" -b "d=$(grep '^SLACK_COOKIE=' ~/.fe-skills/.env | cut -d= -f2-)" -H "Content-Type: application/json" -d '{"channel": "CHANNEL_ID", "text": "MESSAGE_TEXT"}'
```

## Reply in a thread

```bash
curl -s "https://slack.com/api/chat.postMessage" -H "Authorization: Bearer $(grep '^SLACK_TOKEN=' ~/.fe-skills/.env | cut -d= -f2-)" -b "d=$(grep '^SLACK_COOKIE=' ~/.fe-skills/.env | cut -d= -f2-)" -H "Content-Type: application/json" -d '{"channel": "CHANNEL_ID", "thread_ts": "THREAD_TS", "text": "REPLY_TEXT"}'
```

## Add a reaction

```bash
curl -s "https://slack.com/api/reactions.add" -H "Authorization: Bearer $(grep '^SLACK_TOKEN=' ~/.fe-skills/.env | cut -d= -f2-)" -b "d=$(grep '^SLACK_COOKIE=' ~/.fe-skills/.env | cut -d= -f2-)" -H "Content-Type: application/json" -d '{"channel": "CHANNEL_ID", "timestamp": "MESSAGE_TS", "name": "EMOJI_NAME"}'
```

The `name` is the emoji name without colons (e.g., `thumbsup` not `:thumbsup:`).

## List saved items ("Save for later")

```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/saved.py list --pretty
```

With full message content and channel names:

```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/saved.py list --hydrate --pretty
```

Optional: `--count N` to limit results (default 25).

Uses the internal `saved.list` API (not `stars.list`, which is deprecated). Returns uncompleted saved items with:
- `item_id` — channel ID where the message lives
- `ts` — message timestamp
- `date_due` — optional due date (0 if none)
- `state` — `in_progress` for active items
- When `--hydrate`: adds `text`, `user_name`, `channel_name`, `permalink`
