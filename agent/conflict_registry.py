"""
conflict_registry.py
=====================
Inter-guideline conflict registry for ARCagent.

Encodes each guideline's stance on the four registered conflict zones
(GET, CBT, diagnosis_criteria, disease_name), maps fine-grained stances to
broad agreement/conflict directions, and detects when a query and its
retrieved evidence set should surface a guideline conflict or agreement
note to the generation prompt.
"""

from __future__ import annotations

from typing import Dict, List, Set


# ── Guideline conflict detection ───────────────────────────────────────────────

# Known conflict zones between ME/CFS guidelines.
# topic_key → {guideline_id_substring: (stance, short_label)}
KNOWN_CONFLICTS = {
    # ── GET: all guidelines except IQWiG oppose it; IQWiG found limited hint ──
    "GET": {
        "NICE_NG206":          ("strongly_against",        "NICE NG206"),
        "IOM_NAM_2015":        ("not_recommended",         "IOM/NAM 2015"),
        "CCC_2003":            ("caution_avoid_externally_paced", "CCC 2003"),
        "ICC_2012":            ("not_recommended",         "ICC 2012"),
        "IACFSME_PRIMER_2014": ("caution_document_harms",  "IACFS/ME Primer 2014"),
        "CDC_MECFS_FULL":      ("not_recommended",         "CDC"),
        "IQWIG_2023":          ("limited_evidence_unresolved_harm_risk", "IQWiG N21-01"),
    },
    # ── CBT: NICE/CCC/ICC reject as treatment; IQWiG found weak short-term hint ──
    "CBT": {
        "NICE_NG206":          ("not_as_treatment",        "NICE NG206"),
        "IOM_NAM_2015":        ("insufficient_evidence",   "IOM/NAM 2015"),
        "CCC_2003":            ("explicitly_rejected_biopsychosocial_model", "CCC 2003"),
        "ICC_2012":            ("not_recommended",         "ICC 2012"),
        "IACFSME_PRIMER_2014": ("coping_only_not_curative","IACFS/ME Primer 2014"),
        "IQWIG_2023":          ("weak_short_term_hint_only","IQWiG N21-01"),
    },
    # ── Diagnostic criteria: symptom count and cluster requirements vary ───────
    "diagnosis_criteria": {
        "IOM_NAM_2015":        ("3_core_plus_1_of_2",     "IOM/NAM 2015"),
        "NICE_NG206":          ("4_core_symptoms",         "NICE NG206"),
        "CCC_2003":            ("4_domains_plus_2_neuro_plus_2_clusters", "CCC 2003"),
        "ICC_2012":            ("PENE_plus_3_mandatory_categories", "ICC 2012"),
        "CDC_MECFS_FULL":      ("iom_2015_aligned",        "CDC"),
        "IACFSME_PRIMER_2014": ("fukuda_minimum_ccc_preferred", "IACFS/ME Primer 2014"),
    },
    # ── Disease name: ME vs CFS vs ME/CFS vs SEID ────────────────────────────
    "disease_name": {
        "ICC_2012":            ("ME_only_drop_CFS",        "ICC 2012"),
        "CCC_2003":            ("ME_CFS_interchangeable",  "CCC 2003"),
        "NICE_NG206":          ("ME_CFS",                  "NICE NG206"),
        "IOM_NAM_2015":        ("SEID_proposed",           "IOM/NAM 2015"),
        "CDC_MECFS_FULL":      ("ME_CFS",                  "CDC"),
        "IACFSME_PRIMER_2014": ("ME_CFS",                  "IACFS/ME Primer 2014"),
    },
}

CONFLICT_TRIGGERS = {
    # ── GET triggers: expanded to catch clinical phrasing ─────────────────────
    "GET": [
        "graded exercise", "get therapy", "exercise therapy",
        "structured exercise", "exercise programme", "exercise program",
        "can i exercise", "should i exercise", "exercise safe",
        "exercise recommend", "physical activity program",
        "incremental exercise", "activity expansion",
    ],
    # ── CBT triggers: expanded to catch clinical phrasing ─────────────────────
    "CBT": [
        "cognitive behaviour", "cognitive behavior", "cbt",
        "psychotherapy", "psychological treatment",
        "talking therapy", "is cbt helpful", "does cbt work",
        "psychological approach", "cognitive therapy",
    ],
    # ── Diagnosis criteria triggers: expanded ────────────────────────────────
    "diagnosis_criteria": [
        "diagnostic criteria", "case definition", "diagnosis criteria",
        "how is me/cfs diagnosed", "criteria for diagnosis",
        "what criteria", "which criteria", "iom criteria", "nice criteria",
        "ccc criteria", "fukuda", "how do you diagnose",
        "symptoms needed", "required symptoms", "minimum symptoms",
    ],
    # ── Disease name triggers ──────────────────────────────────────────
    "disease_name": [
        "name of the condition", "what to call", "terminology", "me or cfs", "seid",
        "why is it called", "what is the correct name", "me/cfs or cfs",
        "myalgic encephalomyelitis vs", "is it me or cfs",
        "cfs or me", "difference between me and cfs",
        "systemic exertion intolerance", "what does me stand for",
        "why me not cfs", "rename", "name change",
        "encephalomyelitis", "should we call it",
    ],
}



# ── Stance direction grouping ─────────────────────────────────────────────────
# Different stance labels may point in the same direction (all "against GET").
# Map fine-grained stances → broad directions for agreement/conflict detection.
STANCE_DIRECTION: Dict[str, str] = {
    # GET / CBT — all these mean "don't recommend / avoid"
    "strongly_against":                        "against",
    "not_recommended":                         "against",
    "caution":                                 "against",
    "caution_avoid_externally_paced":          "against",
    "caution_document_harms":                  "against",
    "not_as_treatment":                        "against",
    "not_primary":                             "against",
    "explicitly_rejected_biopsychosocial_model": "against",
    "coping_only_not_curative":                "against",
    "insufficient_evidence":                   "against",
    # IQWiG — limited/uncertain support (distinct from "against" or "for")
    "limited_evidence_unresolved_harm_risk":   "uncertain_limited",
    "weak_short_term_hint_only":               "uncertain_limited",
    # Diagnosis criteria — each is a distinct approach (always different)
    "3_core_plus_1_of_2":                      "iom_approach",
    "4_core_symptoms":                         "nice_approach",
    "4_domains_plus_2_neuro_plus_2_clusters":  "ccc_approach",
    "PENE_plus_3_mandatory_categories":        "icc_approach",
    "iom_2015_aligned":                        "iom_approach",
    "fukuda_minimum_ccc_preferred":            "pragmatic_approach",
    # Disease name — each is a distinct naming convention
    "ME_only_drop_CFS":                        "ME_only",
    "ME_CFS_interchangeable":                  "ME_CFS",
    "ME_CFS":                                  "ME_CFS",
    "SEID_proposed":                           "SEID",
}


def detect_conflicts(query: str, guideline_rows: List[Dict]) -> str:
    """
    Given the query and retrieved guideline chunks, detect whether any known
    conflict zones are triggered. Returns a formatted conflict note to inject
    into the prompt, or empty string if no conflicts detected.

    Uses STANCE_DIRECTION to group fine-grained stance labels into broad
    directions before testing agreement vs conflict — so that "strongly_against"
    and "caution_avoid_externally_paced" are both treated as "against".
    """
    q = query.lower()
    present_sources = {row.get("guideline_id", "") for row in guideline_rows}
    tagged_topics: Set[str] = set()
    for row in guideline_rows:
        for t in row.get("conflict_topics", []):
            tagged_topics.add(t)

    conflict_notes = []

    for topic, triggers in CONFLICT_TRIGGERS.items():
        triggered = any(t in q for t in triggers) or topic in tagged_topics
        if not triggered:
            continue

        stances = KNOWN_CONFLICTS.get(topic, {})
        relevant = {
            gid: (stance, label)
            for gid, (stance, label) in stances.items()
            if any(gid in src for src in present_sources)
        }
        if len(relevant) < 2:
            continue

        # Map to broad directions
        directions = {
            gid: STANCE_DIRECTION.get(stance, stance)
            for gid, (stance, label) in relevant.items()
        }
        unique_directions = set(directions.values())

        if len(unique_directions) == 1:
            # All retrieved sources agree directionally → note agreement, cite all
            labels = [label for _, (_, label) in relevant.items()]
            conflict_notes.append(
                f"GUIDELINE AGREEMENT on '{topic}': "
                f"{', '.join(labels)} all have consistent position. "
                "Cite all of them."
            )
        else:
            # Actual directional conflict → group by direction, show clearly
            by_direction: Dict[str, List[str]] = {}
            for gid, (stance, label) in relevant.items():
                direction = directions[gid]
                by_direction.setdefault(direction, []).append(label)
            parts = [f"{direction}: {', '.join(labels)}"
                     for direction, labels in by_direction.items()]
            conflict_notes.append(
                f"⚠ GUIDELINE CONFLICT on '{topic}': "
                + " | ".join(parts)
                + ". You MUST explicitly flag this conflict in your answer."
            )

    if conflict_notes:
        return "\n\nGuideline consistency check:\n" + "\n".join(conflict_notes)
    return ""
