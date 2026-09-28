# retrieval.py  (v2)
# -*- coding: utf-8 -*-
"""
Improvements over v1 (topk_guideline_selection.py):
- focus_terms computed once per query, not twice
- BM25 scores normalised before rule boosting (prevents rule domination)
- authority bonus removed (it was the same for every chunk)
- per-guideline diversity cap (MMR-lite) to avoid all results from NICE
- configurable diversity_cap
- clean public API: GuidelineRetriever + format_evidence_block
"""

from __future__ import annotations

import re
import json
from collections import defaultdict
import textwrap
from typing import List, Dict, Tuple

from rank_bm25 import BM25Okapi


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_jsonl(path: str) -> List[Dict]:
    rows: List[Dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def tokenize(text: str) -> List[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s\-/]", " ", text)
    return [t for t in text.split() if t]


# ---------------------------------------------------------------------------
# Symptom focus extraction
# ---------------------------------------------------------------------------

def extract_focus_terms(query: str) -> Dict[str, bool]:
    q = query.lower()

    def has(*words: str) -> bool:
        return any(w in q for w in words)

    return {
        # ── Core symptom domains ──────────────────────────────────────────
        # Vitality/energy-related terms are given elevated retrieval priority.
        "fatigue": has(
            "fatigue", "tired", "exhausted", "exhaustion", "energy",
            "vitality", "no energy", "low energy", "wired but tired",
        ),
        # PEM is the strongest discriminator between severity groups
        # and the cardinal symptom of ME/CFS (post-exertional malaise).
        "pem": has(
            "pem", "post-exertional", "post exertional", "crash",
            "after activity", "after exertion", "worse the next day",
            "next day", "activity intolerance", "exertion", "boom and bust",
            "activity crash", "energy crash", "relapse after",
            "two day delay", "delayed worsening",
        ),
        "sleep": has("sleep", "unrefreshing", "rested", "wake up", "non-restorative"),
        "cognition": has(
            "brain fog", "memory", "concentration", "focus",
            "cognitive", "thinking", "confusion", "word finding",
        ),
        "orthostatic": has(
            "dizzy", "lightheaded", "standing", "upright",
            "orthostatic", "palpitations", "pots", "dysautonomia",
        ),
        "pain": has("pain", "headache", "muscle", "joint", "tender"),
        # Social function correlates with objective activity measures more
        # strongly than isolated physical-function items, motivating its
        # inclusion as a separate focus dimension.
        "social_function": has(
            "social", "friends", "relationships", "isolation", "housebound",
            "leave the house", "leave home", "can't go out", "activities",
            "participate", "interaction",
        ),
        # Activity limitation is one of the most commonly affected functional
        # domains in ME/CFS and is treated as a distinct focus dimension.
        "activity_limit": has(
            "can't do", "cannot do", "limited activity", "activity limit",
            "bedridden", "bed bound", "bed-bound", "housebound",
            "wheelchair", "daily activities", "usual activities",
            "steps", "walking", "mobility",
        ),
        # Severity indicators: feeds into severity stratification in api_server
        "severe_indicators": has(
            "bedridden", "bed-bound", "housebound", "wheelchair",
            "cannot walk", "very severe", "severe me", "mostly in bed",
            "unable to", "can't get up",
        ),
        "mild_indicators": has(
            "working part-time", "mostly functional", "mild symptoms",
            "mild me", "mild cfs", "managing",
        ),
        # Genomic / biological queries
        "genomic": has(
            "gene", "genetic", "genomic", "dna", "rna", "transcriptomic",
            "epigenetic", "methylation", "snp", "variant", "pathway",
            "mitochondri", "immune", "interferon", "nk cell", "t cell",
            "oxidative", "phosphorylation", "neuroinflammation",
            "biological", "biomarker", "omics", "proteom",
            "why do i", "mechanism", "cause of",
        ),
        "diagnosis_ask": has(
            "diagnosis", "criteria", "could this be", "do i have",
            "sound like", "related to me/cfs", "fit me/cfs",
            "differential", "rule out",
        ),
        "management": has(
            "manage", "management", "treatment", "care", "plan", "help",
            "pacing", "energy envelope", "rest", "rehabilitation",
        ),
    }


# ---------------------------------------------------------------------------
# Query expansion
# ---------------------------------------------------------------------------

def expand_query(query: str, focus: Dict[str, bool]) -> List[str]:
    terms = tokenize(query)

    if focus["fatigue"]:
        terms += ["fatigue", "reduction", "activity", "vitality", "energy", "exhaustion"]
    if focus["pem"]:
        # PEM is the highest-impact symptom domain; most expansive expansion
        terms += [
            "post-exertional", "malaise", "pem", "crash", "exertion",
            "activity", "intolerance", "worsening", "relapse",
            "energy", "boom-bust", "delay",
        ]
    if focus["sleep"]:
        terms += ["sleep", "unrefreshing", "non-restorative", "fatigue"]
    if focus["cognition"]:
        terms += ["cognitive", "brain", "fog", "memory", "concentration", "neurocognitive"]
    if focus["orthostatic"]:
        terms += ["orthostatic", "standing", "upright", "lightheaded", "dizziness", "pots"]
    if focus["pain"]:
        terms += ["pain", "headache", "musculoskeletal"]
    if focus["social_function"]:
        terms += ["social", "function", "activities", "participation", "isolation", "daily"]
    if focus["activity_limit"]:
        terms += ["activity", "limitation", "functional", "impairment", "daily", "usual"]
    if focus["genomic"]:
        terms += [
            "immune", "mitochondrial", "interferon", "pathway",
            "transcriptomic", "biological", "mechanism", "nk-cell",
        ]
    if focus["diagnosis_ask"]:
        terms += ["diagnosis", "criteria", "suspect", "iom", "nice", "differential"]
    if focus["management"]:
        terms += ["management", "care", "support", "pacing", "energy", "envelope"]

    return terms


# ---------------------------------------------------------------------------
# Per-chunk scoring
# ---------------------------------------------------------------------------

# BM25 score range varies widely; normalise to [0, 10] before boosting.
_RULE_BOOST_SCALE = 10.0   # max rule boost ≈ same order as normalised BM25

BAD_PATTERNS = [
    "your responsibility", "all rights reserved", "published:",
    "notice of rights", "local commissioners", "yellow card scheme",
    "recent activity", "see all", "see reviews",
]


def _normalise_bm25(scores: List[float]) -> List[float]:
    max_s = max(scores) if scores else 1.0
    if max_s == 0:
        return [0.0] * len(scores)
    return [s / max_s * _RULE_BOOST_SCALE for s in scores]


def _rule_boost(row: Dict, focus: Dict[str, bool]) -> float:
    merged = " ".join([
        row.get("title", ""),
        row.get("section", ""),
        row.get("text", ""),
        " ".join(row.get("tags", [])),
    ]).lower()

    boost = 0.0

    # ── Empirically-prioritized domains ──────────────────────────────────
    # PEM: strongest severity discriminator and the defining ME/CFS feature.
    if focus["pem"] and any(
        x in merged for x in [
            "post-exertional", "pem", "crash", "exertion", "malaise",
            "activity intolerance", "boom and bust",
        ]
    ):
        boost += 5.0   # highest weight: PEM is the defining feature

    # Social function: a sensitive functional indicator.
    if focus["social_function"] and any(
        x in merged for x in ["social", "function", "activities", "participation"]
    ):
        boost += 3.5

    # Activity limitation: a commonly affected functional domain.
    if focus["activity_limit"] and any(
        x in merged for x in [
            "activity", "limitation", "functional", "impairment",
            "usual activities", "daily activities", "housebound",
        ]
    ):
        boost += 3.5

    # Diagnosis: key entry point for both patients and clinicians
    if focus["diagnosis_ask"] and any(
        x in merged for x in ["criteria", "diagnosis", "diagnostic", "suspect", "iom", "nice"]
    ):
        boost += 4.0

    # Orthostatic: important comorbidity dimension
    if focus["orthostatic"] and any(
        x in merged for x in ["orthostatic", "standing", "upright", "lightheaded", "pots"]
    ):
        boost += 2.5

    # Management: high patient/clinician information need
    if focus["management"] and any(
        x in merged for x in ["management", "care", "support", "plan", "pacing"]
    ):
        boost += 2.0

    # Vitality/energy: boost fatigue chunks that also mention vitality or energy.
    if focus["fatigue"] and any(
        x in merged for x in ["vitality", "energy", "exhaustion", "fatigue"]
    ):
        boost += 1.5

    if focus["sleep"] and "sleep" in merged:
        boost += 1.5

    if focus["cognition"] and any(
        x in merged for x in ["cognitive", "brain fog", "memory", "concentration"]
    ):
        boost += 1.5

    if focus["pain"] and any(x in merged for x in ["pain", "headache"]):
        boost += 1.0

    # ── Genomic chunks: only boost when explicitly queried ───────────────
    if focus["genomic"] and any(
        x in merged for x in [
            "immune", "mitochondr", "interferon", "pathway", "transcriptomic",
            "nk cell", "t cell", "genomic", "epigenetic", "oxidative",
        ]
    ):
        boost += 4.0

    # ── Structural bonuses ───────────────────────────────────────────────
    boost += 0.2 * float(row.get("priority", 3))
    boost += 0.5 * sum(1 for t in row.get("tags", []) if t.lower() in merged)

    # ── Boilerplate penalty ──────────────────────────────────────────────
    text_l = row.get("text", "").lower()
    if any(p in text_l for p in BAD_PATTERNS):
        boost -= 3.0

    return boost


# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------

class GuidelineRetriever:
    """
    BM25 + rule-boosted retriever with per-source diversity cap.

    Parameters
    ----------
    kb_jsonl : str
        Path to guidelines_chunks.jsonl produced by build_guideline_kb.py
    diversity_cap : int
        Maximum number of chunks from any single guideline_id in the result set.
        Defaults to 2 so a 5-result set draws from at least 3 different sources.
    """

    def __init__(self, kb_jsonl: str, diversity_cap: int = 2):
        self.rows = load_jsonl(kb_jsonl)
        self.diversity_cap = diversity_cap

        corpus = []
        for r in self.rows:
            merged = " ".join([
                r.get("title", ""),
                r.get("section", ""),
                r.get("text", ""),
                " ".join(r.get("tags", [])),
            ])
            corpus.append(tokenize(merged))

        self.bm25 = BM25Okapi(corpus)

    def search(self, query: str, top_k: int = 6) -> List[Dict]:
        if not self.rows:
            return []

        # 1. compute focus once
        focus = extract_focus_terms(query)

        # 2. BM25 scores + normalise
        query_terms = expand_query(query, focus)
        raw_scores = self.bm25.get_scores(query_terms).tolist()
        norm_scores = _normalise_bm25(raw_scores)

        # 3. combine BM25 + rule boosts
        scored: List[Tuple[float, Dict]] = []
        for row, ns in zip(self.rows, norm_scores):
            final = ns + _rule_boost(row, focus)
            scored.append((final, row))

        scored.sort(key=lambda x: x[0], reverse=True)

        # 4. diversity-capped selection
        quota: Dict[str, int] = defaultdict(int)
        results: List[Dict] = []
        for _, row in scored:
            if len(results) >= top_k:
                break
            gid = row["guideline_id"]
            if quota[gid] >= self.diversity_cap:
                continue
            quota[gid] += 1
            item = dict(row)
            item["sid"] = str(len(results) + 1)
            results.append(item)

        # 5. if diversity cap left us with < top_k, fill with next-best (no cap)
        if len(results) < top_k:
            used_chunk_ids = {r["chunk_id"] for r in results}
            for _, row in scored:
                if len(results) >= top_k:
                    break
                if row["chunk_id"] in used_chunk_ids:
                    continue
                item = dict(row)
                item["sid"] = str(len(results) + 1)
                results.append(item)

        return results


# ---------------------------------------------------------------------------
# Prompt formatting
# ---------------------------------------------------------------------------

def format_evidence_block(rows: List[Dict]) -> str:
    """
    Format retrieved chunks into a numbered evidence block for the LLM prompt.
    """
    blocks: List[str] = []
    for r in rows:
        blocks.append(
            f"[{r['sid']}] {r['title']} ({r['authority']})\n"
            f"Section: {r.get('section', 'General')}\n"
            f"Text: {r['text']}"
        )
    return "\n\n".join(blocks)


# ---------------------------------------------------------------------------
# CLI smoke-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    kb_path = sys.argv[1] if len(sys.argv) > 1 else "./kb/guidelines_chunks.jsonl"
    query = (
        sys.argv[2]
        if len(sys.argv) > 2
        else (
            "I feel dizzy when I stand up, have severe fatigue, and feel much worse "
            "the day after any activity. Could this be related to ME/CFS?"
        )
    )

    retriever = GuidelineRetriever(kb_path)
    results = retriever.search(query, top_k=5)

    for r in results:
        print(f"[{r['sid']}] {r['guideline_id']} | {r['authority']}")
        print(f"  Section : {r.get('section', '')}")
        print(f"  Words   : {r.get('word_count', '?')}")
        print(f"  Preview : {r['text'][:180]} …")
        print()
