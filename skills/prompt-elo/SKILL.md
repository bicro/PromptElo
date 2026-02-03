---
name: prompt-elo
description: Get detailed Elo scoring breakdown with visual report for your last prompt
allowed-tools:
  - Bash(python3 *)
  - Bash(open *)
  - Write(*)
---

# PromptElo Detailed Analysis

When this skill is invoked, analyze the user's most recent prompt and generate a detailed visual report.

## Instructions

1. First, get the user's most recent prompt from the conversation history. If the skill was invoked with arguments (e.g., `/prompt-elo "my prompt here"`), use that text instead.

2. Run the scorer to get the detailed breakdown:
   ```bash
   echo '{"prompt": "<USER_PROMPT>"}' | python3 ~/.promptelo/client/scorer.py --detailed
   ```

3. Generate an HTML report using the template at `~/.promptelo/skills/prompt-elo/templates/report.html`

4. The report should include:
   - **Overall Elo Score** with tier badge
   - **Radar Chart** showing all 5 criteria (clarity, specificity, context, creativity, novelty)
   - **Score Breakdown** with explanations for each criterion
   - **Improvement Suggestions** based on lowest-scoring areas
   - **Global Ranking** showing percentile among all prompts (if API available)

5. Save the report to a temp file and open it in the browser:
   ```bash
   open /tmp/promptelo_report.html
   ```

## Output Format

Present a summary in the terminal:

```
📊 PromptElo Analysis Complete!

Elo Rating: 1847 ⭐ (Expert)

Score Breakdown:
  Clarity:     ████████░░  82%
  Specificity: ███████░░░  71%
  Context:     █████████░  88%
  Creativity:  ██████░░░░  63%
  Novelty:     ███████░░░  74%

🎯 Top Suggestion: Add more specific technical details to improve specificity.

📈 Global Ranking: Top 15% (of 12,847 prompts)

Full report opened in browser →
```

## Notes

- If the community API is unavailable, novelty will show as "N/A" and use a default value for Elo calculation
- The HTML report includes interactive elements and can be saved for reference
- Suggestions are generated based on which criteria scored lowest
