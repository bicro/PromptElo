# PromptElo Setup

Configure your PromptElo settings interactively.

## Configuration Options

### Server Mode
1. **Global Rankings** (default) - Use the shared PromptElo server at `promptelo-api.onrender.com`
2. **Self-Hosted** - Use your own PromptElo server instance

### Identity
1. **Anonymous** (default) - Auto-generated ID like `anon-abc123def456`
2. **Username** - Set a custom username or email to track your stats

## Instructions

Read the current config from `~/.promptelo/config.json` and help the user update it based on their preferences.

After changes, update the config file with the new values. The config format is:

```json
{
  "server_url": "https://promptelo-api.onrender.com",
  "user_id": "anon-xxx or custom-username",
  "timeout": 5.0,
  "setup_complete": true
}
```

### For Self-Hosted Server
If the user wants to self-host, they need to:
1. Clone the PromptElo repo
2. Deploy the server (see README for Render/Docker instructions)
3. Update `server_url` to their server's URL

### For Custom Username
If the user wants to claim a username:
1. Ask for their preferred username or email
2. Update `user_id` in the config

After making changes, confirm the new settings with the user.
