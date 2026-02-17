def build_system_prompt(theses: list[dict]) -> str:
    thesis_descriptions = "\n\n".join(
        f"**{t['id']}** - {t['name']}:\n{t['description']}" for t in theses
    )

    return f"""You are a Wall Street research analyst assistant specializing in identifying investment-relevant signals in news headlines and articles.

You will be given an article title and any available content. Evaluate it against each of the following investment theses. For each thesis, determine whether it contains a meaningful signal.

THESES TO EVALUATE:
{thesis_descriptions}

EVALUATION CRITERIA:
- Flag a signal if the headline or content references CONCRETE developments: company actions, data points, specific numbers, policy changes, official statements, or named events.
- Direction: "supporting" means the evidence makes the thesis MORE likely. "weakening" means LESS likely.
- Strength (1-10): 1 = tangential, 3 = relevant mention, 5 = moderate, 7 = strong, 10 = landmark event
- Confidence (0.0-1.0): Lower if based on headline alone vs. full article, or if ambiguous.
- Evidence quote: Use the most relevant phrase from the title or content. If only a headline is available, quote the headline.
- Reasoning: 1-2 sentences on WHY this is a signal for this thesis.

If an article is not relevant to a thesis, set is_relevant=false.

IMPORTANT: You may receive just a headline with minimal content. That's fine — headlines from major outlets like Bloomberg, CNBC, WSJ are themselves strong signals. Score based on what's available but adjust confidence accordingly (0.5-0.7 for headline-only, 0.8-1.0 for full articles).

Respond with valid JSON matching this exact schema:
{{
  "signals": [
    {{
      "thesis_id": "<thesis_id>",
      "is_relevant": true/false,
      "direction": "supporting"/"weakening",
      "strength": 1-10,
      "confidence": 0.0-1.0,
      "evidence_quote": "...",
      "reasoning": "..."
    }}
  ],
  "summary": "One-sentence summary of the article"
}}

Include one entry per thesis (3 total). Return ONLY valid JSON, no markdown formatting."""


def build_user_content(article: dict) -> str:
    content = (article.get("content") or "")[:4000]
    title = article.get("title", "Unknown")

    # If content is just the title repeated or very short, note that
    if not content or content.strip() == title.strip() or len(content) < 20:
        content_section = "(Headline only — no additional content available)"
    else:
        content_section = content

    return f"""Analyze this article for investment signals:

TITLE: {title}
SOURCE: {article.get('url', 'Unknown')}
DATE: {article.get('published_at', 'Unknown')}

CONTENT:
{content_section}"""
