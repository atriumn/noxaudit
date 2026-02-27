# Notifications

Noxaudit can send audit summaries via Telegram after each run.

## Telegram Setup

### 1. Create a Bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow the prompts
3. Copy the bot token (looks like `123456789:ABCdefGhIjKlMnOpQrStUvWxYz`)

### 2. Get Your Chat ID

1. Start a conversation with your bot
2. Send any message
3. Visit `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Find `"chat":{"id":YOUR_CHAT_ID}` in the response

### 3. Configure Noxaudit

Set environment variables:

```bash
export TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIjKlMnOpQrStUvWxYz
export TELEGRAM_CHAT_ID=YOUR_CHAT_ID
```

Add to your `noxaudit.yml`:

```yaml
notifications:
  - channel: telegram
    target: "YOUR_CHAT_ID"
```

## Notification Format

After each audit, noxaudit sends a message like:

```
🔒 Security Audit — my-app
3 new findings: 🔴 1 high, 🟡 2 medium

⚠️ SQL interpolation in query builder
   src/db/queries.ts
ℹ️ Console.log with request body
   src/middleware/auth.ts
ℹ️ Permissive CORS in production config
   src/config/cors.ts

✅ 5 previous findings still resolved
```

When there are no new findings:

```
🔒 Security Audit — my-app
No new findings ✓

✅ 5 previous findings still resolved
```

## CI Usage

In GitHub Actions, pass credentials as secrets:

```yaml
- uses: atriumn/noxaudit/action@main
  with:
    anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
    telegram-bot-token: ${{ secrets.TELEGRAM_BOT_TOKEN }}
    telegram-chat-id: ${{ secrets.TELEGRAM_CHAT_ID }}
```

See [GitHub Actions](../integrations/github-actions.md) for the full workflow.

## Multiple Channels

You can configure multiple notification channels:

```yaml
notifications:
  - channel: telegram
    target: "CHAT_ID_1"
  - channel: telegram
    target: "CHAT_ID_2"
```

Each channel receives the same summary.
