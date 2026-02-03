#!/usr/bin/env python3
"""Generate HTML report for PromptElo analysis."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from scorer import analyze_prompt, get_elo_tier


# Template path
TEMPLATE_PATH = Path.home() / ".promptelo" / "skills" / "prompt-elo" / "templates" / "report.html"
OUTPUT_PATH = Path("/tmp/promptelo_report.html")


def get_score_class(score: float) -> str:
    """Get CSS class based on score value."""
    if score >= 0.8:
        return "excellent"
    elif score >= 0.6:
        return "good"
    elif score >= 0.4:
        return "average"
    else:
        return "poor"


def get_tier_name(elo: int) -> str:
    """Get tier name for Elo rating."""
    if elo >= 2200:
        return "Grandmaster"
    elif elo >= 2000:
        return "Master"
    elif elo >= 1800:
        return "Expert"
    elif elo >= 1500:
        return "Advanced"
    elif elo >= 1200:
        return "Intermediate"
    else:
        return "Beginner"


def generate_suggestions(scores: dict) -> str:
    """Generate HTML for improvement suggestions."""
    suggestions_data = {
        "clarity": {
            "icon": "💡",
            "title": "Improve Clarity",
            "text": "Use specific action verbs (create, implement, fix) and avoid vague language like 'something' or 'stuff'. Structure your request in clear sentences."
        },
        "specificity": {
            "icon": "🎯",
            "title": "Add More Details",
            "text": "Include file names, function names, or code snippets. Mention specific technologies, versions, or constraints that are relevant."
        },
        "context": {
            "icon": "📝",
            "title": "Provide More Context",
            "text": "Explain your current situation, what you've tried, and any constraints. Include error messages or relevant background information."
        },
        "creativity": {
            "icon": "✨",
            "title": "Explore Different Approaches",
            "text": "Consider asking about alternative solutions, best practices, or trade-offs. Frame problems in interesting or novel ways."
        },
        "novelty": {
            "icon": "🌟",
            "title": "Try Unique Requests",
            "text": "Your prompt is similar to many others. Consider combining concepts in new ways or exploring less common use cases."
        }
    }

    # Sort by score to show suggestions for lowest-scoring areas
    sorted_scores = sorted(scores.items(), key=lambda x: x[1])

    html = ""
    # Show suggestions for the 2-3 lowest scoring criteria
    for criterion, score in sorted_scores[:3]:
        if score < 0.7:  # Only suggest if below threshold
            data = suggestions_data.get(criterion, {})
            if data:
                html += f"""
                <div class="suggestion-item">
                    <span class="suggestion-icon">{data['icon']}</span>
                    <div class="suggestion-text">
                        <h3>{data['title']}</h3>
                        <p>{data['text']}</p>
                    </div>
                </div>
                """

    if not html:
        html = """
        <div class="suggestion-item">
            <span class="suggestion-icon">🎉</span>
            <div class="suggestion-text">
                <h3>Excellent Prompt!</h3>
                <p>Your prompt scores well across all criteria. Keep up the great work!</p>
            </div>
        </div>
        """

    return html


def generate_report(prompt: str) -> str:
    """Generate HTML report for a prompt.

    Args:
        prompt: The prompt text to analyze

    Returns:
        Path to the generated HTML report
    """
    # Analyze the prompt
    result = analyze_prompt(prompt)
    scores = result["scores"]
    elo = result["elo"]

    # Load template
    if TEMPLATE_PATH.exists():
        template = TEMPLATE_PATH.read_text()
    else:
        # Use embedded template as fallback
        template = get_fallback_template()

    # Calculate percentages
    clarity_pct = int(scores["clarity"] * 100)
    specificity_pct = int(scores["specificity"] * 100)
    context_pct = int(scores["context"] * 100)
    creativity_pct = int(scores["creativity"] * 100)
    novelty_pct = int(scores["novelty"] * 100)

    # Replace template variables
    replacements = {
        "{{ELO_SCORE}}": str(elo),
        "{{TIER_EMOJI}}": get_elo_tier(elo),
        "{{TIER_NAME}}": get_tier_name(elo),
        "{{CLARITY_SCORE}}": f"{scores['clarity']:.2f}",
        "{{SPECIFICITY_SCORE}}": f"{scores['specificity']:.2f}",
        "{{CONTEXT_SCORE}}": f"{scores['context']:.2f}",
        "{{CREATIVITY_SCORE}}": f"{scores['creativity']:.2f}",
        "{{NOVELTY_SCORE}}": f"{scores['novelty']:.2f}",
        "{{CLARITY_PERCENT}}": str(clarity_pct),
        "{{SPECIFICITY_PERCENT}}": str(specificity_pct),
        "{{CONTEXT_PERCENT}}": str(context_pct),
        "{{CREATIVITY_PERCENT}}": str(creativity_pct),
        "{{NOVELTY_PERCENT}}": str(novelty_pct),
        "{{CLARITY_CLASS}}": get_score_class(scores["clarity"]),
        "{{SPECIFICITY_CLASS}}": get_score_class(scores["specificity"]),
        "{{CONTEXT_CLASS}}": get_score_class(scores["context"]),
        "{{CREATIVITY_CLASS}}": get_score_class(scores["creativity"]),
        "{{NOVELTY_CLASS}}": get_score_class(scores["novelty"]),
        "{{SUGGESTIONS}}": generate_suggestions(scores),
        "{{GLOBAL_RANK}}": f"Top {100 - int(result.get('novelty_percentile', 50))}%" if result.get('novelty_percentile') else "N/A",
        "{{TOTAL_PROMPTS}}": "N/A" if not result.get('api_available') else "...",
        "{{AVG_NOVELTY}}": f"{scores['novelty']:.0%}",
        "{{PROMPT_TEXT}}": prompt.replace("<", "&lt;").replace(">", "&gt;"),
        "{{TIMESTAMP}}": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    html = template
    for key, value in replacements.items():
        html = html.replace(key, value)

    # Write output
    OUTPUT_PATH.write_text(html)
    return str(OUTPUT_PATH)


def get_fallback_template() -> str:
    """Return a minimal fallback template if main template is missing."""
    return """<!DOCTYPE html>
<html><head><title>PromptElo Report</title></head>
<body style="font-family: sans-serif; padding: 20px; background: #1e293b; color: white;">
<h1>PromptElo Analysis</h1>
<h2>Elo Score: {{ELO_SCORE}} {{TIER_EMOJI}}</h2>
<ul>
<li>Clarity: {{CLARITY_PERCENT}}%</li>
<li>Specificity: {{SPECIFICITY_PERCENT}}%</li>
<li>Context: {{CONTEXT_PERCENT}}%</li>
<li>Creativity: {{CREATIVITY_PERCENT}}%</li>
<li>Novelty: {{NOVELTY_PERCENT}}%</li>
</ul>
<h3>Prompt:</h3>
<pre>{{PROMPT_TEXT}}</pre>
</body></html>"""


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python report_generator.py <prompt>", file=sys.stderr)
        sys.exit(1)

    prompt = " ".join(sys.argv[1:])
    output_path = generate_report(prompt)
    print(output_path)


if __name__ == "__main__":
    main()
