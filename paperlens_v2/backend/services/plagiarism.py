import logging
"""
PaperLens — Multi-Agent Plagiarism Detection
=============================================

ARCHITECTURE:
  6 agents across 3 tiers — all FREE, no license needed.

  TIER 1 — Academic Database Agents (billions of papers, free APIs)
  ┌─────────────────────┬────────────────────────────────────────────────┐
  │ Agent               │ Database            │ Strength                 │
  ├─────────────────────┼────────────────────────────────────────────────┤
  │ Semantic Scholar    │ 200M+ papers        │ Best semantic search     │
  │ OpenAlex            │ 240M+ works         │ Open access, fast        │
  │ CrossRef            │ 150M+ DOI records   │ Best for citations       │
  │ CORE.ac.uk          │ 30M+ open access    │ Full text available      │
  └─────────────────────┴────────────────────────────────────────────────┘

  TIER 2 — Web / General Agents
  ┌─────────────────────┬────────────────────────────────────────────────┐
  │ Agent               │ Source              │ Strength                 │
  ├─────────────────────┼────────────────────────────────────────────────┤
  │ Wikipedia           │ Wikipedia API       │ Catches copied intros    │
  └─────────────────────┴────────────────────────────────────────────────┘

  TIER 3 — Local Text Analysis Agent
  ┌─────────────────────┬────────────────────────────────────────────────┐
  │ Agent               │ What it catches                                │
  ├─────────────────────┼────────────────────────────────────────────────┤
  │ Self-Plagiarism     │ Repeated paragraphs within the document        │
  └─────────────────────┴────────────────────────────────────────────────┘

STRATEGY:
  - Extract 6 key phrases spread across the document
  - All 5 database agents query in parallel
  - Each match is deduplicated and scored with Jaccard similarity
  - Cross-agent corroboration: a match found by 2+ agents gets boosted
  - Final score = weighted blend of match quality + phrase hit rate
"""

import asyncio
import re
import hashlib
import httpx
from typing import List, Optional

logger = logging.getLogger(__name__)
TIMEOUT = 15.0
HEADERS = {
    "User-Agent": "PaperLens/1.0 (paperlens.in; mailto:hello@paperlens.in)"
}

STOP_WORDS = {
    "the","a","an","and","or","in","of","to","is","are","was","were",
    "for","on","at","by","with","this","that","which","from","be","as",
    "it","its","not","but","have","has","had","will","would","could",
    "should","may","might","can","do","does","did","so","if","than",
    "then","also","both","each","more","most","other","some","such",
    "no","nor","only","own","same","too","very","just","because","as",
    "until","while","about","against","between","into","through","during",
    "before","after","above","below","to","from","up","down","out","off",
    "over","under","again","further","once",
}


# ══════════════════════════════════════════════════════════════════════════════
# PHRASE EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════

def _extract_key_phrases(text: str, n: int = 6) -> List[str]:
    """
    Extract n representative phrases spread across the document.
    Skips reference sections, citations, and very short sentences.
    """
    # Remove references section (common in papers)
    text = re.sub(r'\n(References|Bibliography|Works Cited)[\s\S]*$', '', text, flags=re.IGNORECASE)

    sentences = re.split(r'(?<=[.!?])\s+', text)
    filtered = []
    for s in sentences:
        s = s.strip()
        # Skip: too short, too long, citations, numbered lists, URLs
        if not (10 <= len(s.split()) <= 45):
            continue
        if re.match(r'^\[?\d+[\].]', s):       # [1] or 1.
            continue
        if re.search(r'https?://', s):
            continue
        if re.search(r'\bet al\.', s[:30]):     # citation
            continue
        filtered.append(s)

    if not filtered:
        return []

    # Spread picks evenly across document (start, middle, end all covered)
    seen = set()
    unique = []
    for s in filtered:
        key = s[:55].lower()
        if key not in seen:
            seen.add(key)
            unique.append(s)

    if len(unique) <= n:
        return unique

    step = len(unique) / n
    return [unique[int(i * step)] for i in range(n)]


# ══════════════════════════════════════════════════════════════════════════════
# SIMILARITY
# ══════════════════════════════════════════════════════════════════════════════

def _jaccard(a: str, b: str) -> float:
    """Jaccard similarity between two text strings (word-level, no stopwords)."""
    if not a or not b:
        return 0.0
    a_words = set(re.sub(r'[^\w\s]', '', a.lower()).split()) - STOP_WORDS
    b_words = set(re.sub(r'[^\w\s]', '', b.lower()).split()) - STOP_WORDS
    if not a_words or not b_words:
        return 0.0
    inter = a_words & b_words
    union = a_words | b_words
    return len(inter) / len(union)


def _phrase_in_title(phrase: str, title: str) -> float:
    """Higher-weight check: query phrase in paper title."""
    return _jaccard(phrase, title) * 1.3  # boost title matches


# ══════════════════════════════════════════════════════════════════════════════
# TIER 1 — ACADEMIC DATABASE AGENTS
# ══════════════════════════════════════════════════════════════════════════════

async def _agent_semantic_scholar(phrase: str) -> List[dict]:
    """Semantic Scholar — 200M papers, best semantic search."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as client:
            resp = await client.get(
                "https://api.semanticscholar.org/graph/v1/paper/search",
                params={
                    "query": phrase[:200],
                    "limit": 4,
                    "fields": "title,authors,year,openAccessPdf,abstract,externalIds",
                },
            )
        if resp.status_code != 200:
            return []
        results = []
        for paper in resp.json().get("data", []):
            title    = paper.get("title", "")
            abstract = paper.get("abstract") or ""
            sim = max(
                _phrase_in_title(phrase, title),
                _jaccard(phrase, abstract[:500]),
            )
            if sim < 0.08:
                continue
            doi = paper.get("externalIds", {}).get("DOI", "")
            url = (
                paper.get("openAccessPdf", {}).get("url")
                or (f"https://doi.org/{doi}" if doi else "")
                or f"https://semanticscholar.org/paper/{paper.get('paperId','')}"
            )
            results.append({
                "title":      title,
                "authors":    [a.get("name","") for a in paper.get("authors",[])[:3]],
                "year":       paper.get("year"),
                "similarity": min(sim, 1.0),
                "source":     "Semantic Scholar",
                "url":        url,
                "agents":     {"semantic_scholar"},
            })
        return results
    except Exception as e:
        logger.warning("[\1] agent error: %s", e)
        return []


async def _agent_openalex(phrase: str) -> List[dict]:
    """OpenAlex — 240M+ works, fully open, fast."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as client:
            resp = await client.get(
                "https://api.openalex.org/works",
                params={
                    "search": phrase[:200],
                    "per-page": 4,
                    "select": "title,authorships,publication_year,doi,abstract_inverted_index",
                },
            )
        if resp.status_code != 200:
            return []
        results = []
        for work in resp.json().get("results", []):
            title = work.get("title") or ""

            # Reconstruct abstract from inverted index
            inv = work.get("abstract_inverted_index") or {}
            if inv:
                max_pos = max(max(positions) for positions in inv.values()) + 1
                abstract_words = [""] * max_pos
                for word, positions in inv.items():
                    for pos in positions:
                        if pos < max_pos:
                            abstract_words[pos] = word
                abstract = " ".join(abstract_words)
            else:
                abstract = ""

            sim = max(
                _phrase_in_title(phrase, title),
                _jaccard(phrase, abstract[:500]),
            )
            if sim < 0.08:
                continue
            doi = work.get("doi", "")
            results.append({
                "title":      title,
                "authors":    [a.get("author",{}).get("display_name","") for a in work.get("authorships",[])[:3]],
                "year":       work.get("publication_year"),
                "similarity": min(sim, 1.0),
                "source":     "OpenAlex",
                "url":        f"https://doi.org/{doi}" if doi else "",
                "agents":     {"openalex"},
            })
        return results
    except Exception as e:
        logger.warning("[\1] agent error: %s", e)
        return []


async def _agent_crossref(phrase: str) -> List[dict]:
    """CrossRef — 150M+ DOI records, best for finding citation sources."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as client:
            resp = await client.get(
                "https://api.crossref.org/works",
                params={"query": phrase[:200], "rows": 4,
                        "select": "title,author,published,DOI"},
            )
        if resp.status_code != 200:
            return []
        results = []
        for item in resp.json().get("message", {}).get("items", []):
            title_list = item.get("title", [""])
            title = title_list[0] if title_list else ""
            sim = _phrase_in_title(phrase, title)
            if sim < 0.08:
                continue
            doi = item.get("DOI", "")
            pub = item.get("published", {}).get("date-parts", [[None]])[0]
            authors = [
                f"{a.get('given','')} {a.get('family','')}".strip()
                for a in item.get("author", [])[:3]
            ]
            results.append({
                "title":      title,
                "authors":    authors,
                "year":       pub[0] if pub else None,
                "similarity": min(sim, 1.0),
                "source":     "CrossRef",
                "url":        f"https://doi.org/{doi}" if doi else "",
                "agents":     {"crossref"},
            })
        return results
    except Exception as e:
        logger.warning("[\1] agent error: %s", e)
        return []


async def _agent_core(phrase: str) -> List[dict]:
    """
    CORE.ac.uk — 30M+ open access papers with full text.
    No key needed for basic search.
    Get key (optional, higher limits): https://core.ac.uk/services/api
    """
    from config import get_settings
    settings = get_settings()
    try:
        params = {"q": phrase[:200], "limit": 4}
        headers = dict(HEADERS)
        if settings.CORE_API_KEY:
            headers["Authorization"] = f"Bearer {settings.CORE_API_KEY}"

        async with httpx.AsyncClient(timeout=TIMEOUT, headers=headers) as client:
            resp = await client.get("https://api.core.ac.uk/v3/search/works", params=params)
        if resp.status_code != 200:
            return []
        results = []
        for item in resp.json().get("results", []):
            title    = item.get("title") or ""
            abstract = item.get("abstract") or ""
            sim = max(
                _phrase_in_title(phrase, title),
                _jaccard(phrase, abstract[:500]),
            )
            if sim < 0.08:
                continue
            results.append({
                "title":      title,
                "authors":    item.get("authors", [])[:3],
                "year":       item.get("yearPublished"),
                "similarity": min(sim, 1.0),
                "source":     "CORE",
                "url":        item.get("downloadUrl") or item.get("sourceFulltextUrls", [""])[0],
                "agents":     {"core"},
            })
        return results
    except Exception as e:
        logger.warning("[\1] agent error: %s", e)
        return []


# ══════════════════════════════════════════════════════════════════════════════
# TIER 2 — WEB AGENT
# ══════════════════════════════════════════════════════════════════════════════

async def _agent_wikipedia(phrase: str) -> List[dict]:
    """
    Wikipedia API — catches plagiarised intros, definitions, background sections.
    Free, unlimited.
    """
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as client:
            resp = await client.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": phrase[:200],
                    "srlimit": 3,
                    "srprop": "snippet|title",
                    "format": "json",
                },
            )
        if resp.status_code != 200:
            return []
        results = []
        for item in resp.json().get("query", {}).get("search", []):
            title   = item.get("title", "")
            snippet = re.sub(r'<[^>]+>', '', item.get("snippet", ""))  # strip HTML
            sim = max(
                _phrase_in_title(phrase, title),
                _jaccard(phrase, snippet),
            )
            if sim < 0.12:  # stricter threshold for Wikipedia
                continue
            results.append({
                "title":      f"Wikipedia: {title}",
                "authors":    ["Wikipedia Contributors"],
                "year":       None,
                "similarity": min(sim, 1.0),
                "source":     "Wikipedia",
                "url":        f"https://en.wikipedia.org/wiki/{title.replace(' ','_')}",
                "agents":     {"wikipedia"},
            })
        return results
    except Exception as e:
        logger.warning("[\1] agent error: %s", e)
        return []


# ══════════════════════════════════════════════════════════════════════════════
# TIER 3 — LOCAL AGENT
# ══════════════════════════════════════════════════════════════════════════════

def _agent_self_plagiarism(text: str) -> dict:
    """
    Detects repeated passages within the same document.
    Common in thesis chapters reusing intro material.
    Returns a score 0.0–1.0 where 1.0 = heavily self-plagiarised.
    """
    paragraphs = [p.strip() for p in text.split('\n\n') if len(p.split()) > 10]
    if len(paragraphs) < 4:
        return {"score": 0.0, "repeated_pairs": []}

    repeated = []
    n = len(paragraphs)
    for i in range(n):
        for j in range(i+1, n):
            sim = _jaccard(paragraphs[i], paragraphs[j])
            if sim > 0.55:  # >55% word overlap = likely copy-paste
                repeated.append({
                    "para_a": paragraphs[i][:120] + "...",
                    "para_b": paragraphs[j][:120] + "...",
                    "similarity": round(sim, 3),
                })

    score = min(1.0, len(repeated) / max(1, n // 3))
    return {"score": round(score, 3), "repeated_pairs": repeated[:5]}


# ══════════════════════════════════════════════════════════════════════════════
# ENSEMBLE ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════

async def check_plagiarism(text: str) -> dict:
    """
    Run all plagiarism agents in parallel. Merge, deduplicate, cross-validate.

    Returns:
    {
        "plag_score":        0.34,
        "label":             "moderate",
        "matches":           [...],      # top sources with similarity %
        "self_plagiarism":   {...},
        "phrases_checked":   6,
        "agents_responded":  5,
        "corroborated":      2,          # matches found by 2+ agents
        "interpretation":    "..."
    }
    """
    phrases = _extract_key_phrases(text, n=6)

    if not phrases:
        return {
            "plag_score": 0.0,
            "label": "none",
            "matches": [],
            "self_plagiarism": {"score": 0.0, "repeated_pairs": []},
            "phrases_checked": 0,
            "agents_responded": 0,
            "corroborated": 0,
            "interpretation": "Could not extract meaningful phrases to check.",
        }

    # ── Run all agents for all phrases in parallel ──────────────────────────
    tasks = []
    for phrase in phrases:
        tasks.extend([
            _agent_semantic_scholar(phrase),
            _agent_openalex(phrase),
            _agent_crossref(phrase),
            _agent_core(phrase),
            _agent_wikipedia(phrase),
        ])

    all_results_nested = await asyncio.gather(*tasks, return_exceptions=True)
    agents_responded = set()
    raw_matches = []

    for result in all_results_nested:
        if isinstance(result, Exception) or not result:
            continue
        for match in result:
            agent_set = match.get("agents", set())
            agents_responded.update(agent_set)
            raw_matches.append(match)

    # ── Self-plagiarism (local, synchronous) ────────────────────────────────
    self_plag = _agent_self_plagiarism(text)

    # ── Deduplicate + cross-validate ────────────────────────────────────────
    merged: dict[str, dict] = {}
    for match in raw_matches:
        key = match["title"].lower()[:60].strip()
        if not key:
            continue
        if key in merged:
            merged[key]["similarity"] = max(merged[key]["similarity"], match["similarity"])
            merged[key]["agents"].update(match.get("agents", set()))
            merged[key]["found_by_n"] = len(merged[key]["agents"])
        else:
            match["found_by_n"] = 1
            merged[key] = dict(match)

    # Sort by similarity (boost corroborated matches)
    def _match_score(m: dict) -> float:
        corroboration_bonus = 0.05 * (m.get("found_by_n", 1) - 1)
        return m["similarity"] + corroboration_bonus

    unique_matches = sorted(merged.values(), key=_match_score, reverse=True)

    # Convert agent sets to lists for JSON serialisation
    for m in unique_matches:
        m["agents"] = sorted(m.get("agents", set()))

    top_matches = unique_matches[:8]
    corroborated_count = sum(1 for m in top_matches if m.get("found_by_n", 1) >= 2)

    # ── Aggregate score ──────────────────────────────────────────────────────
    if not top_matches:
        plag_score = 0.0
    else:
        top3_sim     = [m["similarity"] for m in top_matches[:3]]
        avg_top3     = sum(top3_sim) / len(top3_sim)
        phrase_hits  = len(unique_matches)
        hit_rate     = min(1.0, phrase_hits / (len(phrases) * 1.5))
        corr_bonus   = 0.05 * corroborated_count

        plag_score = round(
            (avg_top3 * 0.55) + (hit_rate * 0.35) + (corr_bonus * 0.10), 3
        )

    # Blend in self-plagiarism score (weight: 20%)
    self_plag_score = self_plag.get("score", 0.0)
    if self_plag_score > 0:
        plag_score = round(plag_score * 0.80 + self_plag_score * 0.20, 3)

    plag_score = min(plag_score, 1.0)
    label      = _plag_label(plag_score)

    interpretation = _build_plag_interpretation(
        plag_score, label, top_matches, corroborated_count,
        len(agents_responded), len(phrases), self_plag_score
    )

    return {
        "plag_score":       plag_score,
        "label":            label,
        "matches":          top_matches,
        "self_plagiarism":  self_plag,
        "phrases_checked":  len(phrases),
        "agents_responded": len(agents_responded),
        "corroborated":     corroborated_count,
        "interpretation":   interpretation,
    }


def _plag_label(score: float) -> str:
    if score < 0.08:
        return "none"
    elif score < 0.20:
        return "low"
    elif score < 0.40:
        return "moderate"
    elif score < 0.65:
        return "high"
    else:
        return "very_high"


def _build_plag_interpretation(
    score: float,
    label: str,
    matches: list,
    corroborated: int,
    n_agents: int,
    n_phrases: int,
    self_score: float,
) -> str:
    if label == "none":
        return (
            f"No significant matches found across {n_agents} academic databases "
            f"({n_phrases} phrases checked). This document appears original."
        )
    top_source = matches[0]["title"][:60] if matches else "unknown"
    base = (
        f"Found {len(matches)} matching sources across {n_agents} databases. "
        f"Top match: '{top_source}'. "
    )
    if corroborated:
        base += f"{corroborated} match(es) confirmed by multiple databases (higher confidence). "
    if self_score > 0.2:
        base += "Significant internal repetition detected (possible self-plagiarism). "
    if label == "low":
        base += "Overall similarity is low — likely incidental overlap with common academic phrases."
    elif label == "moderate":
        base += "Moderate similarity — review flagged sections and ensure proper citation."
    elif label == "high":
        base += "High similarity detected. Immediate review and citation check recommended."
    else:
        base += "Very high similarity. This document may contain substantial uncited content."
    return base
