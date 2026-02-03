#!/usr/bin/env python3
"""PromptElo scorer - analyzes prompts and calculates Elo ratings.

This script is designed to be called by the Claude Code UserPromptSubmit hook.
It reads the prompt from stdin (JSON format) and outputs the Elo badge.
"""

import json
import re
import sys
from typing import Optional

from api import score_prompt, PromptEloAPIError


# Scoring weights
WEIGHTS = {
    "clarity": 0.25,
    "specificity": 0.25,
    "context": 0.20,
    "creativity": 0.15,
    "novelty": 0.15
}

# Elo calculation constants
ELO_BASE = 1200  # Average Elo
ELO_RANGE = 1200  # Range (600-1800 maps to 0-1 scores, extended to 2400 for exceptional)


def score_clarity(prompt: str) -> float:
    """Score the clarity of a prompt (0-1).

    Measures:
    - Clear sentence structure
    - Absence of ambiguous language
    - Use of specific verbs vs vague ones
    """
    score = 0.5  # Base score

    # Positive: Clear action verbs
    clear_verbs = [
        r'\b(create|build|write|implement|add|remove|fix|update|refactor|test|debug|explain|analyze|compare|list|show|find|search|generate|convert|parse|validate|check)\b'
    ]
    for pattern in clear_verbs:
        if re.search(pattern, prompt, re.IGNORECASE):
            score += 0.1

    # Positive: Question words (shows clear intent)
    if re.search(r'\b(how|what|why|where|when|which|can you|could you|please)\b', prompt, re.IGNORECASE):
        score += 0.1

    # Negative: Vague language
    vague_patterns = [
        r'\b(something|somehow|maybe|probably|sort of|kind of|stuff|things)\b',
        r'\b(it|this|that)\b(?!\s+\w+)',  # Unclear pronouns at start
    ]
    for pattern in vague_patterns:
        if re.search(pattern, prompt, re.IGNORECASE):
            score -= 0.1

    # Positive: Well-structured (multiple sentences or clear sections)
    sentences = re.split(r'[.!?]+', prompt)
    if len([s for s in sentences if s.strip()]) >= 2:
        score += 0.1

    # Positive: Uses formatting (code blocks, bullets, etc.)
    if re.search(r'```|`[^`]+`|\n[-*]\s|\n\d+\.', prompt):
        score += 0.1

    return max(0.0, min(1.0, score))


def score_specificity(prompt: str) -> float:
    """Score the specificity of a prompt (0-1).

    Measures:
    - Technical details provided
    - File/function names mentioned
    - Concrete requirements stated
    """
    score = 0.3  # Base score

    # Positive: File paths or names
    if re.search(r'[\w/]+\.\w{1,5}\b|[\w/]+/[\w/]+', prompt):
        score += 0.15

    # Positive: Function/class/variable names
    if re.search(r'\b[a-z]+[A-Z]\w*|[A-Z][a-z]+[A-Z]\w*|\b\w+_\w+\b', prompt):
        score += 0.1

    # Positive: Code snippets
    if '```' in prompt or re.search(r'`[^`]+`', prompt):
        score += 0.15

    # Positive: Technical terms
    tech_terms = [
        r'\b(function|class|method|variable|parameter|argument|return|type|interface|module|package|import|export|async|await|promise|callback|API|endpoint|database|query|schema|migration)\b',
        r'\b(error|exception|bug|issue|crash|undefined|null|NaN|stack trace)\b',
        r'\b(test|unit test|integration|mock|stub|fixture|assertion)\b'
    ]
    for pattern in tech_terms:
        if re.search(pattern, prompt, re.IGNORECASE):
            score += 0.05

    # Positive: Numbers/quantities (specific requirements)
    if re.search(r'\b\d+\b', prompt):
        score += 0.1

    # Positive: Longer prompts tend to be more specific
    word_count = len(prompt.split())
    if word_count > 50:
        score += 0.1
    elif word_count > 20:
        score += 0.05

    return max(0.0, min(1.0, score))


def score_context(prompt: str) -> float:
    """Score the context provided in a prompt (0-1).

    Measures:
    - Background information
    - Current state/situation
    - Constraints mentioned
    """
    score = 0.3  # Base score

    # Positive: Background indicators
    background_patterns = [
        r'\b(currently|right now|at the moment|existing|current)\b',
        r'\b(I have|I\'m using|I\'m working on|my project|our codebase)\b',
        r'\b(because|since|as|due to|the reason)\b',
        r'\b(want to|need to|trying to|goal is|objective is)\b'
    ]
    for pattern in background_patterns:
        if re.search(pattern, prompt, re.IGNORECASE):
            score += 0.1

    # Positive: Constraints mentioned
    constraint_patterns = [
        r'\b(must|should|cannot|shouldn\'t|don\'t want|avoid|without|only|prefer)\b',
        r'\b(compatible|support|work with|integrate)\b',
        r'\b(performance|security|scalability|maintainability)\b'
    ]
    for pattern in constraint_patterns:
        if re.search(pattern, prompt, re.IGNORECASE):
            score += 0.1

    # Positive: Environment/setup details
    if re.search(r'\b(version|v\d|node|python|npm|pip|docker|OS|linux|mac|windows)\b', prompt, re.IGNORECASE):
        score += 0.1

    # Positive: Error messages or stack traces
    if re.search(r'error:|Error:|exception|traceback|at line \d+', prompt, re.IGNORECASE):
        score += 0.15

    return max(0.0, min(1.0, score))


def score_creativity(prompt: str) -> float:
    """Score the creativity/novelty of approach in a prompt (0-1).

    Measures:
    - Novel problem framing
    - Interesting combinations
    - Non-standard requests
    """
    score = 0.4  # Base score

    # Positive: Exploratory language
    exploratory = [
        r'\b(explore|experiment|try|investigate|consider|alternative|different approach|other ways)\b',
        r'\b(what if|could we|is there a way|would it be possible)\b',
        r'\b(optimize|improve|enhance|better|best practice|elegant|clean)\b'
    ]
    for pattern in exploratory:
        if re.search(pattern, prompt, re.IGNORECASE):
            score += 0.1

    # Positive: Combination of concepts
    concepts = [
        r'\b(combine|merge|integrate|connect|bridge|link)\b',
        r'\b(and|with|plus|alongside|together)\b.*\b(and|with|plus)\b'
    ]
    for pattern in concepts:
        if re.search(pattern, prompt, re.IGNORECASE):
            score += 0.1

    # Positive: Unique/creative keywords
    creative_keywords = [
        r'\b(creative|novel|unique|innovative|unconventional|clever)\b',
        r'\b(design|architect|pattern|strategy|approach)\b'
    ]
    for pattern in creative_keywords:
        if re.search(pattern, prompt, re.IGNORECASE):
            score += 0.1

    # Negative: Very common/boilerplate requests (slightly reduce)
    common_patterns = [
        r'^(fix|help|how do I|what is)\s',
        r'\b(hello world|todo app|CRUD|basic|simple example)\b'
    ]
    for pattern in common_patterns:
        if re.search(pattern, prompt, re.IGNORECASE):
            score -= 0.05

    return max(0.0, min(1.0, score))


def calculate_local_scores(prompt: str) -> dict:
    """Calculate all local scoring criteria."""
    return {
        "clarity": score_clarity(prompt),
        "specificity": score_specificity(prompt),
        "context": score_context(prompt),
        "creativity": score_creativity(prompt)
    }


def calculate_elo(scores: dict) -> int:
    """Calculate the Elo rating from component scores.

    Args:
        scores: Dict with clarity, specificity, context, creativity, novelty (all 0-1)

    Returns:
        Elo rating (integer, typically 600-2400)
    """
    # Calculate weighted average
    weighted_sum = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)

    # Map to Elo scale
    # 0.0 -> 600, 0.5 -> 1200, 1.0 -> 1800
    # Exceptional scores can go higher
    elo = ELO_BASE + (weighted_sum - 0.5) * ELO_RANGE

    # Bonus for consistently high scores (synergy bonus)
    min_score = min(scores.values())
    if min_score > 0.7:
        elo += 100  # Well-rounded prompt bonus
    if min_score > 0.8:
        elo += 100  # Exceptional all-around

    return int(max(0, min(2400, elo)))


def get_elo_tier(elo: int) -> tuple[str, str]:
    """Get the tier name and emoji for an Elo rating."""
    if elo >= 2200:
        return ("LEGENDARY", "🏆")
    elif elo >= 2000:
        return ("MASTER", "⭐")
    elif elo >= 1800:
        return ("EXPERT", "🌟")
    elif elo >= 1500:
        return ("SKILLED", "✨")
    elif elo >= 1200:
        return ("RISING", "📝")
    else:
        return ("NOVICE", "📋")


def get_novelty_label(percentile: float) -> tuple[str, str]:
    """Get a label and emoji for novelty percentile."""
    if percentile >= 95:
        return ("LEGENDARY", "💎")
    elif percentile >= 85:
        return ("RARE", "🌟")
    elif percentile >= 70:
        return ("UNCOMMON", "✨")
    elif percentile >= 30:
        return ("COMMON", "📊")
    else:
        return ("FREQUENT", "📈")


def format_badge(elo: int, novelty_percentile: Optional[float] = None) -> str:
    """Format the Elo badge with dramatic slot machine styling."""
    tier_name, tier_emoji = get_elo_tier(elo)

    # Build the dramatic badge
    lines = []
    lines.append("🎰 ━━━━━━━━━━━━━━━━━━━━━ 🎰")
    lines.append(f"   {tier_emoji} {elo} • {tier_name} {tier_emoji}")

    if novelty_percentile is not None:
        novelty_name, novelty_emoji = get_novelty_label(novelty_percentile)
        if novelty_percentile >= 85:
            lines.append(f"   {novelty_emoji} TOP {100 - int(novelty_percentile)}% • {novelty_name} {novelty_emoji}")
        else:
            lines.append(f"   {novelty_emoji} Novelty: {novelty_name}")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━")

    return "\n".join(lines)


def analyze_prompt(prompt: str) -> dict:
    """Analyze a prompt and return full scoring breakdown.

    Args:
        prompt: The prompt text to analyze

    Returns:
        Dict with all scores, Elo, and formatted badge
    """
    # Calculate local scores
    local_scores = calculate_local_scores(prompt)

    # Try to get novelty score from community server
    novelty_score = 0.5  # Default if API unavailable
    novelty_percentile = None
    api_available = False

    try:
        result = score_prompt(prompt)
        novelty_score = result["novelty"]["novelty_score"]
        novelty_percentile = result["novelty"]["percentile"]
        api_available = True
    except PromptEloAPIError:
        # API unavailable, use default novelty
        pass

    # Combine all scores
    all_scores = {
        **local_scores,
        "novelty": novelty_score
    }

    # Calculate Elo
    elo = calculate_elo(all_scores)

    # Format badge
    badge = format_badge(elo, novelty_percentile)

    return {
        "scores": all_scores,
        "elo": elo,
        "badge": badge,
        "novelty_percentile": novelty_percentile,
        "api_available": api_available
    }


def main():
    """Main entry point for hook invocation.

    Reads JSON from stdin: {"prompt": "..."}
    Outputs: Plain text badge (visible) + JSON additionalContext (for Claude)
    """
    try:
        # Read input from stdin
        input_data = sys.stdin.read()
        if not input_data.strip():
            # No input, exit silently
            return

        data = json.loads(input_data)
        prompt = data.get("prompt", "")

        if not prompt:
            return

        # Analyze the prompt
        result = analyze_prompt(prompt)

        # Output JSON with systemMessage (visible in normal mode)
        output = {
            "systemMessage": result["badge"]
        }
        print(json.dumps(output))

    except json.JSONDecodeError:
        # Invalid JSON input, exit silently
        pass
    except Exception as e:
        # Log error but don't crash the hook
        sys.stderr.write(f"PromptElo error: {e}\n")


if __name__ == "__main__":
    main()
