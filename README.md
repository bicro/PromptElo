# PromptElo

A Claude Code extension that analyzes and scores user prompts with chess-style Elo ratings.

## Features

- **Automatic Elo Badge**: Every prompt you submit gets an Elo rating displayed inline
- **5-Criteria Scoring**: Clarity, Specificity, Context, Creativity, and Novelty
- **Global Novelty Detection**: Compare your prompts against a community database using embeddings
- **Detailed Reports**: Run `/prompt-elo` for visual HTML reports with radar charts
- **Privacy-Preserving**: Only embeddings are stored, not raw prompts

## Installation

### Quick Install (Plugin)

```bash
# Install the PromptElo plugin
claude plugin install promptelo
```

That's it! Elo badges will appear automatically on every prompt.

### Manual Install

```bash
# Clone the repository
git clone https://github.com/promptelo/promptelo
cd promptelo

# Run the install script
./scripts/install.sh
```

## Usage

### Automatic Badge

After installation, every prompt you submit will show an Elo badge:

```
[PromptElo: 1847 ⭐ | Top 15% Novelty 🌟]
```

### Detailed Analysis

Run the skill for a comprehensive breakdown:

```
/prompt-elo
```

This opens an HTML report with:
- Radar chart of all 5 criteria
- Score breakdown with visual bars
- Improvement suggestions
- Global ranking

## Elo Rating Scale

| Rating | Tier | Description |
|--------|------|-------------|
| 2200+ | 🏆 Grandmaster | Exceptional prompts |
| 2000-2199 | ⭐ Master | Outstanding quality |
| 1800-1999 | 🌟 Expert | High quality |
| 1500-1799 | ✨ Advanced | Above average |
| 1200-1499 | 📝 Intermediate | Average |
| 0-1199 | 📋 Beginner | Room for improvement |

## Scoring Criteria

| Criterion | Weight | What It Measures |
|-----------|--------|------------------|
| Clarity | 25% | Clear intent, specific verbs, good structure |
| Specificity | 25% | Technical details, file/function names, code snippets |
| Context | 20% | Background info, constraints, error messages |
| Creativity | 15% | Novel framing, exploratory questions |
| Novelty | 15% | Uniqueness compared to all prompts (via embeddings) |

## Self-Hosting the Server

If you want to run your own embedding server:

```bash
cd server

# Copy environment template
cp .env.example .env

# Add your OpenAI API key and database URL
# Edit .env with your values

# Run with Docker Compose
docker-compose up -d
```

Then configure the client to use your server:

```bash
# Set environment variable
export PROMPTELO_SERVER_URL="https://your-server.com"

# Or edit config file
echo '{"server_url": "https://your-server.com"}' > ~/.promptelo/config.json
```

## Configuration

Configuration file: `~/.promptelo/config.json`

```json
{
  "server_url": "https://promptelo-api.example.com",
  "user_id": null,
  "timeout": 5.0
}
```

Environment variables (take precedence over config file):
- `PROMPTELO_SERVER_URL` - Server URL
- `PROMPTELO_USER_ID` - User ID for personal stats

## API Reference

The community server exposes these endpoints:

### POST /api/v1/score

Score a prompt for novelty.

Request:
```json
{
  "prompt": "Your prompt text",
  "user_id": "optional-user-id"
}
```

Response:
```json
{
  "novelty": {
    "novelty_score": 0.73,
    "percentile": 68.5,
    "similar_count": 12,
    "is_novel": false
  },
  "total_prompts": 12847,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### GET /api/v1/stats

Get global statistics.

### GET /api/v1/health

Health check endpoint.

## Privacy

PromptElo is designed with privacy in mind:

- **No raw prompts stored**: Only embedding vectors are saved
- **Embeddings are not reversible**: Cannot reconstruct original text
- **Optional user IDs**: Track personal stats anonymously
- **Self-hosting available**: Run your own server for full control

## Development

### Project Structure

```
promptelo/
├── .claude-plugin/          # Plugin configuration
│   ├── plugin.json
│   └── marketplace.json
├── hooks/
│   └── hooks.json           # UserPromptSubmit hook
├── skills/
│   └── prompt-elo/
│       ├── SKILL.md         # Detailed analysis skill
│       └── templates/
│           └── report.html  # Visual report template
├── client/                  # Scoring client
│   ├── scorer.py            # Main scoring logic
│   ├── api.py               # Server API client
│   ├── config.py            # Configuration
│   └── report_generator.py  # HTML report generator
├── server/                  # Community server
│   ├── main.py              # FastAPI application
│   ├── embeddings.py        # OpenAI integration
│   ├── database.py          # PostgreSQL + pgvector
│   ├── models.py            # Pydantic models
│   ├── requirements.txt
│   ├── Dockerfile
│   └── docker-compose.yml
├── scripts/
│   └── install.sh           # Installation script
└── README.md
```

### Running Tests

```bash
# Client tests
cd client
python -m pytest

# Server tests
cd server
python -m pytest
```

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- Built for [Claude Code](https://claude.ai/claude-code)
- Embeddings powered by OpenAI
- Vector storage with pgvector
