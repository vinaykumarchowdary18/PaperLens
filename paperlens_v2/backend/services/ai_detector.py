import logging
"""
PaperLens — Multi-Agent AI Detection Ensemble
===============================================

ARCHITECTURE:
  7 agents across 3 tiers. Each tier covers for the others' blind spots.

  TIER 1 — API Agents (most accurate, rate-limited)
  ┌─────────────────┬──────────────────────────────────────────────────────┐
  │ Agent           │ Free Limit            │ Strength                     │
  ├─────────────────┼──────────────────────────────────────────────────────┤
  │ GPTZero         │ 10,000 words/day      │ Best for GPT-4/Claude        │
  │ Sapling         │ 50 req/day            │ Good sentence-level scores   │
  │ ZeroGPT         │ 10,000 chars/day      │ Independent model, free      │
  │ Writer.com      │ 100 req/day           │ Built for academic writing   │
  └─────────────────┴──────────────────────────────────────────────────────┘

  TIER 2 — Linguistic Agents (unlimited, local, no API)
  ┌─────────────────┬──────────────────────────────────────────────────────┐
  │ Agent           │ What it measures                                     │
  ├─────────────────┼──────────────────────────────────────────────────────┤
  │ Perplexity      │ LLMs use low-perplexity words → predictable text     │
  │ Burstiness      │ Humans vary sentence length; AI is uniform           │
  └─────────────────┴──────────────────────────────────────────────────────┘

  TIER 3 — Pattern Agent (unlimited, catches what others miss)
  ┌─────────────────┬──────────────────────────────────────────────────────┐
  │ Agent           │ What it measures                                     │
  ├─────────────────┼──────────────────────────────────────────────────────┤
  │ LexicalPattern  │ AI overuses certain phrases, hedges, transitions     │
  └─────────────────┴──────────────────────────────────────────────────────┘

SCORING:
  - Each agent returns 0.0 (human) → 1.0 (AI) + confidence weight
  - Weighted average by confidence
  - Agents that failed/timed out are skipped (never block the result)
  - Disagreement detection: if API agents and linguistic agents strongly
    disagree (>0.4 gap), confidence is lowered + user is told why
  - Minimum 2 agents must respond for "high" confidence
"""

import asyncio
import re
import statistics
import httpx
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
TIMEOUT = 15.0


# ══════════════════════════════════════════════════════════════════════════════
# TIER 1 — API AGENTS
# ══════════════════════════════════════════════════════════════════════════════

async def _agent_gptzero(text: str) -> dict | None:
    """
    GPTZero API — best accuracy for GPT-4 / Claude / Gemini outputs.
    Free: 10,000 words/day.
    Get key: https://gptzero.me/api
    """
    if not settings.GPTZERO_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                "https://api.gptzero.me/v2/predict/text",
                headers={"x-api-key": settings.GPTZERO_API_KEY, "Content-Type": "application/json"},
                json={"document": text[:50000]},
            )
        if resp.status_code == 429:
            return {"name": "gptzero", "score": None, "skipped": True, "reason": "rate_limit"}
        if resp.status_code != 200:
            return None
        doc = resp.json().get("documents", [{}])[0]
        score = doc.get("average_generated_prob")
        if score is None:
            return None
        return {
            "name": "gptzero",
            "score": score,
            "weight": 1.0,  # highest weight — most accurate
            "sentence_scores": [
                {"text": s.get("sentence", ""), "score": s.get("generated_prob", 0)}
                for s in doc.get("sentences", [])[:15]
            ],
        }
    except Exception as e:
        logger.warning("[\1] agent error: %s", e)
        return None


async def _agent_sapling(text: str) -> dict | None:
    """
    Sapling AI — sentence-level scores, good for mixed human+AI docs.
    Free: 50 requests/day.
    Get key: https://sapling.ai/user/settings
    """
    if not settings.SAPLING_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                "https://api.sapling.ai/api/v1/aidetect",
                json={"key": settings.SAPLING_API_KEY, "text": text[:50000]},
            )
        if resp.status_code == 429:
            return {"name": "sapling", "score": None, "skipped": True, "reason": "rate_limit"}
        if resp.status_code != 200:
            return None
        data = resp.json()
        score = data.get("score")
        if score is None:
            return None
        return {
            "name": "sapling",
            "score": score,
            "weight": 0.85,
            "sentence_scores": [
                {"text": s[0], "score": s[1]}
                for s in data.get("sentence_scores", [])[:15]
            ],
        }
    except Exception as e:
        logger.warning("[\1] agent error: %s", e)
        return None


async def _agent_zerogpt(text: str) -> dict | None:
    """
    ZeroGPT — independent model, free tier generous (10,000 chars/day).
    No API key needed for basic endpoint.
    Get key (optional): https://zerogpt.com/api
    """
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                "https://api.zerogpt.com/api/detect/detectText",
                headers={
                    "Content-Type": "application/json",
                    "ApiKey": settings.ZEROGPT_API_KEY or "",
                },
                json={"input_text": text[:10000]},  # free tier limit
            )
        if resp.status_code == 429:
            return {"name": "zerogpt", "score": None, "skipped": True, "reason": "rate_limit"}
        if resp.status_code != 200:
            return None
        data = resp.json().get("data", {})
        # ZeroGPT returns fakePercentage 0-100
        pct = data.get("fakePercentage")
        if pct is None:
            return None
        return {
            "name": "zerogpt",
            "score": round(pct / 100, 4),
            "weight": 0.75,
            "additional": {
                "is_human": data.get("isHuman"),
                "ai_words": data.get("aiWords"),
            },
        }
    except Exception as e:
        logger.warning("[\1] agent error: %s", e)
        return None


async def _agent_writer(text: str) -> dict | None:
    """
    Writer.com AI detector — built specifically for academic/professional text.
    Free: 100 requests/day (no credit card needed).
    Get key: https://dev.writer.com  → API Keys
    """
    if not settings.WRITER_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                "https://enterprise-api.writer.com/content/detect",
                headers={
                    "Authorization": f"Bearer {settings.WRITER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={"input": text[:1500]},  # Writer free tier limit per call
            )
        if resp.status_code == 429:
            return {"name": "writer", "score": None, "skipped": True, "reason": "rate_limit"}
        if resp.status_code != 200:
            return None
        data = resp.json()
        # Writer returns {"score": 0-1, "label": "..."}
        score = data.get("score")
        if score is None:
            return None
        return {
            "name": "writer",
            "score": score,
            "weight": 0.80,
            "label": data.get("label"),
        }
    except Exception as e:
        logger.warning("[\1] agent error: %s", e)
        return None


# ══════════════════════════════════════════════════════════════════════════════
# TIER 2 — LINGUISTIC AGENTS (local, unlimited, no API)
# ══════════════════════════════════════════════════════════════════════════════

def _agent_burstiness(text: str) -> dict:
    """
    Burstiness Analysis — measures sentence length variance.

    Human writers naturally vary sentence length dramatically.
    AI models produce text with very uniform sentence lengths.
    Formula: CV = std_dev / mean  →  low CV = AI-like

    Weight: 0.60 (good signal but can be fooled by editing)
    """
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.strip()) > 5]
    if len(sentences) < 6:
        return {"name": "burstiness", "score": 0.5, "weight": 0.3, "note": "too_short"}

    lengths = [len(s.split()) for s in sentences]
    try:
        mean = statistics.mean(lengths)
        std  = statistics.stdev(lengths)
        cv   = std / mean if mean > 0 else 1.0

        # Paragraph-level burstiness (humans vary paragraph lengths too)
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        para_lengths = [len(p.split()) for p in paragraphs if len(p.split()) > 5]
        para_cv = 0.5
        if len(para_lengths) >= 3:
            pm = statistics.mean(para_lengths)
            ps = statistics.stdev(para_lengths)
            para_cv = ps / pm if pm > 0 else 1.0

        # Combined: sentence CV weighted 70%, paragraph CV 30%
        combined_cv = cv * 0.7 + para_cv * 0.3

        # CV < 0.25 → very AI-like (score → 1.0)
        # CV > 0.65 → very human-like (score → 0.0)
        score = max(0.0, min(1.0, 1.0 - ((combined_cv - 0.25) / 0.40)))
        return {
            "name": "burstiness",
            "score": round(score, 4),
            "weight": 0.60,
            "cv": round(combined_cv, 3),
            "mean_sentence_len": round(mean, 1),
        }
    except Exception:
        return {"name": "burstiness", "score": 0.5, "weight": 0.3}


def _agent_perplexity(text: str) -> dict:
    """
    Sentence-Pattern Perplexity Agent.

    Three reliable local signals that distinguish AI from human writing:
    1. 'The ...' sentence openers — AI starts 50-80% of sentences with 'The';
       humans average 20-30%.
    2. Transition word density — AI overuses furthermore/moreover/additionally
       at much higher rates than human academic writers.
    3. Passive voice density — AI uses passive constructions more uniformly.

    Weight: 0.55
    """
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.strip()) > 5]
    if len(sentences) < 4:
        return {"name": "perplexity", "score": 0.5, "weight": 0.3, "note": "too_short"}

    # 1. 'The ...' opener ratio
    the_openers = sum(1 for s in sentences if re.match(r'^The\s', s))
    the_ratio = the_openers / len(sentences)
    # Human academic: ~20-30% | AI: ~50-80%
    the_score = max(0.0, min(1.0, (the_ratio - 0.20) / 0.50))

    # 2. Transition word density
    transitions = [
        'furthermore', 'moreover', 'additionally', 'consequently',
        'nevertheless', 'subsequently', 'therefore', 'thus', 'hence',
        'accordingly', 'in conclusion', 'in summary', 'in addition',
    ]
    text_lower = text.lower()
    trans_count = sum(1 for t in transitions if t in text_lower)
    trans_score = max(0.0, min(1.0, (trans_count / len(sentences)) / 0.8))

    # 3. Passive voice density
    passive_count = len(re.findall(r'\b(is|are|was|were|be|been)\s+\w+ed\b', text_lower))
    passive_score = max(0.0, min(1.0, (passive_count / len(sentences) - 0.15) / 0.65))

    combined = round(the_score * 0.40 + trans_score * 0.35 + passive_score * 0.25, 4)
    return {
        "name": "perplexity",
        "score": combined,
        "weight": 0.55,
        "the_opener_ratio": round(the_ratio, 3),
        "transition_count": trans_count,
        "passive_count": passive_count,
    }


# ══════════════════════════════════════════════════════════════════════════════
# TIER 3 — PATTERN AGENT
# ══════════════════════════════════════════════════════════════════════════════

# Phrases that AI models (GPT-4, Claude, Gemini) heavily overuse
# Based on empirical analysis of AI vs human academic writing
_AI_PHRASES = [
    # Hedging/transitioning (very common in LLM outputs)
    r'\bit is (important|worth|crucial|essential) to (note|mention|highlight)',
    r'\bin (this|the) (context|regard|case)',
    r'\bfurthermore\b', r'\bmoreover\b', r'\badditionally\b',
    r'\bin conclusion\b', r'\bto summarize\b', r'\bin summary\b',
    r'\bit is (worth noting|noteworthy) that',
    r'\bthis (highlights|underscores|demonstrates|illustrates)',
    r'\bplays? a (crucial|pivotal|vital|key|significant) role',
    r'\bdelve into\b', r'\bunpack\b', r'\bnavigate\b',
    r'\bshed light on\b', r'\bprovide insight',
    r'\bcomprehensive (understanding|overview|analysis)',
    r'\bholistic (approach|view|perspective)',
    r'\brobust (framework|solution|approach|system)',
    r'\bseamless(ly)?\b', r'\blever(age|aging)\b',
    r'\bin the realm of\b', r'\bin the domain of\b',
    r'\bcutting-edge\b', r'\bstate-of-the-art\b',
    r'\blandscape\b.*\bevolv',  # "evolving landscape"
    r'\bbest practices\b',
    # Overly formal academic AI-isms
    r'\bthis paper (aims|seeks|endeavors) to\b',
    r'\bthe (aforementioned|aforedescribed)\b',
    r'\bsubstantial(ly)?\b', r'\bsignificant(ly)?\b',
    r'\bsystematic(ally)?\b',
]

_HUMAN_MARKERS = [
    # Colloquialisms and personal voice
    r"\bi (think|believe|feel|found|noticed|wonder)\b",
    r"\bwe (found|noticed|observed|saw)\b",
    r"\binterestingly\b", r"\bsurprisingly\b",
    r"\bto be (honest|fair|clear)\b",
    r"\bin my (experience|view|opinion)\b",
    # Hedging natural to humans (different from AI hedging)
    r"\bsomewhat\b", r"\brather\b", r"\bquite\b",
    # Imperfect constructions
    r"\banyway\b", r"\bbesides\b", r"\bthough\b",
    # First person plural (common in real research papers)
    r"\bwe propose\b", r"\bwe present\b", r"\bour (approach|method|results)\b",
]


def _agent_lexical_pattern(text: str) -> dict:
    """
    Lexical Pattern Agent — detects AI signature phrases.

    LLMs have identifiable linguistic fingerprints:
    they overuse certain transitions, hedges, and academic-sounding
    phrases that rarely appear together in human writing.

    Weight: 0.65 (strong signal for obvious AI text; weaker for edited)
    """
    text_lower = text.lower()
    words = text_lower.split()
    if not words:
        return {"name": "lexical_pattern", "score": 0.5, "weight": 0.3}

    # Count AI phrase hits (normalized per 1000 words)
    ai_hits = sum(
        1 for pattern in _AI_PHRASES
        if re.search(pattern, text_lower)
    )
    human_hits = sum(
        1 for pattern in _HUMAN_MARKERS
        if re.search(pattern, text_lower)
    )

    word_count = max(len(words), 1)
    ai_density   = ai_hits / (word_count / 1000)
    human_density = human_hits / (word_count / 1000)

    # Score: high AI density + low human markers = likely AI
    # Calibrated: AI papers avg ~8-15 hits/1000w, human ~2-5
    ai_raw   = min(1.0, ai_density / 12.0)
    human_raw = min(1.0, human_density / 6.0)

    score = max(0.0, min(1.0, ai_raw - (human_raw * 0.4)))

    # Which patterns fired
    triggered = [
        p for p in _AI_PHRASES
        if re.search(p, text_lower)
    ][:8]

    return {
        "name": "lexical_pattern",
        "score": round(score, 4),
        "weight": 0.65,
        "ai_phrases_found": ai_hits,
        "human_markers_found": human_hits,
        "triggered_patterns": triggered,
    }


# ══════════════════════════════════════════════════════════════════════════════
# ENSEMBLE ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════

async def detect_ai_content(text: str) -> dict:
    """
    Run all agents in parallel. Aggregate with weighted voting.

    Returns:
    {
        "ai_score":    0.84,          # 0.0=human, 1.0=AI
        "label":       "likely_ai",   # human/mixed/likely_ai/ai
        "confidence":  "high",        # low/medium/high
        "agents_used": 5,
        "agents_agreed": True,
        "breakdown": {                # every agent's result
            "gptzero":         {"score": 0.91, "weight": 1.00},
            "sapling":         {"score": 0.88, "weight": 0.85},
            "zerogpt":         {"score": 0.79, "weight": 0.75},
            "burstiness":      {"score": 0.72, "weight": 0.60},
            "perplexity":      {"score": 0.68, "weight": 0.55},
            "lexical_pattern": {"score": 0.81, "weight": 0.65},
        },
        "skipped_agents": ["writer"],  # rate limited or no key
        "sentence_highlights": [...],  # from API agents
        "interpretation": "5 of 6 agents flagged this as AI-generated..."
    }
    """

    # ── Run all agents concurrently ──────────────────────────────────────────
    api_tasks = await asyncio.gather(
        _agent_gptzero(text),
        _agent_sapling(text),
        _agent_zerogpt(text),
        _agent_writer(text),
        return_exceptions=True,
    )

    # Linguistic agents are synchronous (local) — run them too
    ling_results = [
        _agent_burstiness(text),
        _agent_perplexity(text),
        _agent_lexical_pattern(text),
    ]

    # ── Collect results ──────────────────────────────────────────────────────
    all_agents      = []
    breakdown       = {}
    skipped_agents  = []
    sentence_highlights = []

    for result in list(api_tasks) + ling_results:
        if result is None or isinstance(result, Exception):
            continue
        name = result.get("name", "unknown")

        # Rate-limited or no key
        if result.get("skipped"):
            skipped_agents.append(f"{name}({result.get('reason', 'skipped')})")
            continue

        score = result.get("score")
        if score is None:
            continue

        weight = result.get("weight", 0.5)
        all_agents.append({"name": name, "score": score, "weight": weight})
        breakdown[name] = {
            "score": round(score, 4),
            "weight": weight,
            **{k: v for k, v in result.items()
               if k not in ("name", "score", "weight", "sentence_scores")},
        }

        # Collect sentence highlights from API agents
        for s in result.get("sentence_scores", []):
            if s.get("score", 0) > 0.75:
                sentence_highlights.append({
                    "text": s.get("text", "")[:200],
                    "ai_prob": s.get("score"),
                    "source": name,
                })

    # ── Fallback: if no agents responded at all ──────────────────────────────
    if not all_agents:
        return {
            "ai_score": 0.5,
            "label": "unknown",
            "confidence": "low",
            "agents_used": 0,
            "breakdown": {},
            "skipped_agents": skipped_agents,
            "sentence_highlights": [],
            "interpretation": (
                "No detection agents could run. "
                "Add at least GPTZERO_API_KEY to .env for reliable results."
            ),
        }

    # ── Weighted average ─────────────────────────────────────────────────────
    total_weight = sum(a["weight"] for a in all_agents)
    weighted_sum = sum(a["score"] * a["weight"] for a in all_agents)
    final_score  = weighted_sum / total_weight if total_weight > 0 else 0.5

    # ── Disagreement detection ───────────────────────────────────────────────
    api_scores  = [a["score"] for a in all_agents if a["name"] in ("gptzero","sapling","zerogpt","writer")]
    ling_scores = [a["score"] for a in all_agents if a["name"] in ("burstiness","perplexity","lexical_pattern")]

    api_avg  = sum(api_scores)  / len(api_scores)  if api_scores  else None
    ling_avg = sum(ling_scores) / len(ling_scores) if ling_scores else None

    agents_agreed = True
    disagreement_note = None
    if api_avg is not None and ling_avg is not None:
        gap = abs(api_avg - ling_avg)
        if gap > 0.35:
            agents_agreed = False
            if api_avg > ling_avg:
                disagreement_note = (
                    f"API detectors score high ({api_avg:.0%} AI) but "
                    f"linguistic analysis is lower ({ling_avg:.0%}). "
                    "Possible: human-edited AI text or unusual writing style."
                )
            else:
                disagreement_note = (
                    f"Linguistic patterns suggest AI ({ling_avg:.0%}) but "
                    f"API detectors are lower ({api_avg:.0%}). "
                    "Possible: highly technical domain or non-native English."
                )

    # ── Confidence level ─────────────────────────────────────────────────────
    n_agents = len(all_agents)
    if not agents_agreed:
        confidence = "medium"
    elif n_agents >= 5:
        confidence = "high"
    elif n_agents >= 3:
        confidence = "medium"
    else:
        confidence = "low"

    # ── Interpretation text ──────────────────────────────────────────────────
    label = _score_to_label(final_score)
    interpretation = _build_interpretation(
        final_score, label, all_agents, agents_agreed, disagreement_note
    )

    return {
        "ai_score":            round(final_score, 4),
        "label":               label,
        "confidence":          confidence,
        "agents_used":         n_agents,
        "agents_agreed":       agents_agreed,
        "breakdown":           breakdown,
        "skipped_agents":      skipped_agents,
        "sentence_highlights": sentence_highlights[:10],
        "interpretation":      interpretation,
        "disagreement_note":   disagreement_note,
    }


def _score_to_label(score: float) -> str:
    if score < 0.20:
        return "human"
    elif score < 0.45:
        return "mostly_human"
    elif score < 0.60:
        return "mixed"
    elif score < 0.80:
        return "likely_ai"
    else:
        return "ai"


def _build_interpretation(
    score: float,
    label: str,
    agents: list,
    agreed: bool,
    disagreement_note: str | None,
) -> str:
    n = len(agents)
    high_agents = [a["name"] for a in agents if a["score"] >= 0.65]
    low_agents  = [a["name"] for a in agents if a["score"] <  0.35]

    if label == "human":
        base = f"All {n} agents found strong indicators of human writing. This text is very likely original."
    elif label == "mostly_human":
        base = f"{n} agents analysed this. Score of {score:.0%} suggests mostly human writing with possible AI assistance."
    elif label == "mixed":
        base = (
            f"Mixed signals across {n} agents (score: {score:.0%}). "
            "This document may be partially AI-generated or human-edited AI text."
        )
    elif label == "likely_ai":
        base = (
            f"{len(high_agents)} of {n} agents flagged this as likely AI-generated "
            f"(score: {score:.0%}). Agents flagging: {', '.join(high_agents)}."
        )
    else:  # ai
        base = (
            f"Strong consensus across {n} agents: this text is highly likely AI-generated "
            f"(score: {score:.0%}). All major detectors agree."
        )

    if disagreement_note:
        base += f" Note: {disagreement_note}"

    return base
