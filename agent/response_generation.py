"""
response_generation.py
=======================
Dual-mode response generation for ARCagent (patient / clinician modes).

Builds the system + user prompt for the base LLM given a query, the
retrieved evidence block (from retrieval.GuidelineRetriever), and the
inter-guideline conflict note (from conflict_registry.detect_conflicts).

Patient mode uses plain language, cautious hedging, and declines requests
for specific drug doses or individual prognosis. Clinician mode uses
clinical terminology, explicit guideline references, and differential
diagnosis structure. Both modes require inline source citations and
explicit dual-source attribution when a conflict is detected.
"""

from __future__ import annotations

from typing import Dict, List

from conflict_registry import detect_conflicts


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

PATIENT_SYSTEM_PROMPT = (
    "You are a clinically careful ME/CFS information assistant. "
    "Prefer the retrieved guideline evidence as your primary source. If retrieved evidence does not cover a specific point, you may supplement with established clinical knowledge but must flag it as not from retrieved sources. "
    "Insert inline bracketed citations such as [1], [2] immediately after "
    "each sentence or clause that relies on evidence. "
    "Do not cite PMIDs, raw URLs, or source type labels. "
    "If the retrieved evidence does not contain enough information to answer "
    "the user's question, say so explicitly rather than speculating. "
    "Do not diagnose. Use cautious wording such as 'consistent with', "
    "'overlap with', or 'suggestive of'. "
    "Use plain, accessible language suitable for a general audience. "
    "CITATION RULE — if multiple guidelines address the same point and they agree, "
    "cite all of them together, e.g. 'Most guidelines recommend pacing [1][3][5].' "
    "If guidelines disagree, explicitly flag the conflict: "
    "'Guidelines differ on this point: [source A] recommends X, while [source B] recommends Y.' "
    "Never suppress a citation because another guideline says the same thing. "
    "Answer in English. Keep the response focused and concise. "
    "SCOPE RULE — if the question asks for specific drug doses, surgical procedures, "
    "recreational drug safety, precise individual prognosis, or treatments not supported "
    "by any retrieved guideline, you MUST decline to answer even if retrieved content "
    "seems partially relevant. Retrieved evidence does not override scope boundaries."
)

# Clinician-facing: clinical terminology, guideline references, differential thinking
CLINICIAN_SYSTEM_PROMPT = (
    "You are a specialist ME/CFS clinical decision support assistant communicating "
    "with a qualified healthcare professional. "
    "Prefer retrieved guideline evidence as your primary source. If retrieved evidence is insufficient for a specific point, supplement with established clinical knowledge but flag it explicitly as not from retrieved sources. "
    "Insert inline bracketed citations such as [1], [2] immediately after "
    "each sentence or clause that relies on evidence. "
    "Do not cite PMIDs, raw URLs, or source type labels. "
    "If the retrieved evidence is insufficient, state this explicitly. "
    "Use precise clinical terminology when helpful, but answer in natural prose. "
    "Do not reproduce source text, evidence blocks, tables, HTML tags, or pipe-delimited formatting. "
    "Do not use heading-style labels such as 'Short answer', 'Key criteria', 'Work-up', or similar. "
    "CITATION RULE — when multiple guidelines address the same clinical point: "
    "(a) if they agree, cite ALL relevant sources together, e.g. '[1][2][4]'; "
    "(b) if they disagree, you MUST explicitly state the conflict: "
    "'[Source A] recommends X [1], whereas [Source B] does not recommend this [3].' "
    "Never omit a citation because another source says the same thing. "
    "Flag guideline conflicts prominently — this is clinically important. "
    "Answer directly in one concise paragraph, followed by a short bullet list only if clinically useful. "
    "Keep the response brief and practical unless the user explicitly asks for more detail. "
    "CRITICAL: If the retrieved evidence does NOT include NICE NG206 or IOM 2015, explicitly state that those guidelines could not be retrieved and your answer may be incomplete. "
    "NEVER claim guidelines 'endorse' or 'recommend' CBT as a treatment for ME/CFS — all major current guidelines (NICE NG206, CCC 2003, ICC 2012) recommend against CBT as a primary treatment. "
    "Answer in English. "
    "SCOPE RULE — if the question requests specific drug doses, surgical procedures, "
    "recreational drug safety, precise individual prognosis, or treatments unsupported "
    "by retrieved guidelines, decline to answer and explain why, even if retrieved "
    "content seems partially relevant. Retrieved evidence does not override scope boundaries."
)

SYSTEM_PROMPTS = {
    "patient":   PATIENT_SYSTEM_PROMPT,
    "clinician": CLINICIAN_SYSTEM_PROMPT,
}


# ---------------------------------------------------------------------------
# Focus extraction (mirrors retrieval.extract_focus_terms; used to decide
# which mode-specific context notes to attach to the prompt)
# ---------------------------------------------------------------------------

def extract_user_focus(q: str) -> Dict[str, bool]:
    q = q.lower()

    def has(*words: str) -> bool:
        return any(w in q for w in words)

    return {
        "pem": has(
            "pem", "post-exertional", "post exertional", "crash",
            "after activity", "after exertion", "worse the next day",
            "next day", "activity intolerance", "exertion", "boom and bust",
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
        "social_function": has(
            "social", "friends", "relationships", "isolation", "housebound",
            "leave the house", "leave home", "can't go out", "activities",
            "participate", "interaction",
        ),
        "activity_limit": has(
            "can't do", "cannot do", "limited activity", "activity limit",
            "bedridden", "bed bound", "bed-bound", "housebound",
            "wheelchair", "daily activities", "usual activities",
            "steps", "walking", "mobility",
        ),
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
# Severity inference
# ---------------------------------------------------------------------------

def infer_severity(query: str, history: list) -> str:
    """
    Infer approximate severity from the query and recent conversation
    history. Returns: 'severe' | 'moderate' | 'mild' | 'unknown'.
    """
    combined = query.lower()
    for m in history[-4:]:
        if m.get("role") == "user":
            combined += " " + m.get("content", "").lower()

    severe_signals = [
        "bedridden", "bed-bound", "bed bound", "housebound", "house-bound",
        "wheelchair", "cannot walk", "very severe", "mostly in bed",
        "unable to get up", "severe me", "severe cfs",
    ]
    mild_signals = [
        "working part-time", "work part time", "mostly functional",
        "mild symptoms", "mild me", "mild cfs", "still working",
        "managing daily tasks", "can drive", "walking most days",
    ]

    n_severe = sum(1 for s in severe_signals if s in combined)
    n_mild   = sum(1 for s in mild_signals   if s in combined)

    if n_severe >= 1:
        return "severe"
    if n_mild >= 1:
        return "mild"
    if any(s in combined for s in ["moderate", "partly housebound", "limited activity"]):
        return "moderate"
    return "unknown"


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def build_messages(
    query: str,
    guideline_rows: List[Dict],
    history: List[Dict],
    mode: str = "patient",
) -> List[Dict]:
    """
    Build the [system, ..., user] message list for the base LLM.

    guideline_rows is the retrieved-and-formatted evidence (see
    retrieval.format_evidence_block); history is the prior conversation
    turns, used only for severity inference.
    """
    from retrieval import format_evidence_block

    focus        = extract_user_focus(query)
    evidence     = format_evidence_block(guideline_rows)
    is_clinician = (mode == "clinician")
    severity     = infer_severity(query, history)

    # ── Focus notes (mode-aware) ───────────────────────────────────────
    focus_lines = []
    if focus["pem"]:
        focus_lines.append(
            "Clinician query relates to PEM / post-exertional symptom "
            "exacerbation. Draw on the empirical activity-management "
            "evidence in the knowledge base when characterising crash "
            "patterns and recovery time."
            if is_clinician else
            "User emphasises post-exertional worsening / crashes."
        )
    if focus["sleep"]:
        focus_lines.append(
            "Query relates to non-restorative sleep / sleep architecture disturbance."
            if is_clinician else
            "User emphasises unrefreshing sleep."
        )
    if focus["cognition"]:
        focus_lines.append(
            "Query relates to neurocognitive impairment / cognitive dysfunction. "
            "Neuroinflammation is documented in ME/CFS and provides biological "
            "grounding for cognitive symptoms."
            if is_clinician else
            "User emphasises cognitive difficulties / brain fog."
        )
    if focus["orthostatic"]:
        focus_lines.append(
            "Query relates to orthostatic intolerance / dysautonomia / POTS. "
            "Autonomic dysfunction and POTS are well-documented comorbidities "
            "in ME/CFS cohorts."
            if is_clinician else
            "User emphasises dizziness or standing-related symptoms."
        )
    if focus["social_function"]:
        focus_lines.append(
            "Query touches on social/functional participation. Social "
            "participation is a sensitive functional indicator and should "
            "be weighed alongside physical-function measures."
            if is_clinician else
            "User mentions difficulty with social activities or participation."
        )
    if focus["activity_limit"]:
        focus_lines.append(
            "Patient reports significant activity limitation. Activity "
            "limitation is one of the most commonly affected functional "
            "domains in ME/CFS."
            if is_clinician else
            "User reports difficulty with daily activities."
        )
    if focus["genomic"]:
        focus_lines.append(
            "Query is mechanistic/biological — draw on the genomic evidence "
            "chunks, which summarise pathway-level findings from a "
            "monozygotic-twin re-analysis controlling for genetic confounding."
            if is_clinician else
            "User is asking about the biological basis or mechanism of their symptoms."
        )
    if focus["diagnosis_ask"]:
        focus_lines.append(
            "Clinician is seeking diagnostic guidance — include IOM/NAM 2015 and NICE NG206 "
            "criteria comparison, differential diagnosis considerations, and red flags."
            if is_clinician else
            "User is asking whether their symptoms sound like ME/CFS — avoid sounding diagnostic."
        )
    if focus["management"]:
        focus_lines.append(
            "Query relates to management — include pacing/energy envelope principles, "
            "guidance on avoiding graded exercise therapy, and specialist referral indications."
            if is_clinician else
            "User is asking how to manage their symptoms."
        )

    # ── Severity stratification notes ───────────────────────────────────
    severity_note = ""
    if severity == "severe":
        if is_clinician:
            severity_note = (
                "\n[SEVERITY FLAG — SEVERE]: Patient presentation suggests severe ME/CFS "
                "(housebound/bedridden indicators detected). Standard activity-monitoring "
                "metrics (step-count thresholds) underestimate functional decline in severe "
                "patients due to a floor effect, since their baseline activity leaves limited "
                "downward range. Prioritise specialist referral, avoid prescriptive physical "
                "activity targets, and recommend very conservative energy management with "
                "specialist supervision."
            )
        else:
            severity_note = (
                "\n[Note for response]: User may have severe ME/CFS. Emphasise that their "
                "experience is valid and recognised, that very severe presentations are "
                "documented in the medical literature, and that specialist care is important. "
                "Do not suggest activity-based approaches without framing around energy management."
            )
    elif severity == "mild":
        if is_clinician:
            severity_note = (
                "\n[SEVERITY CONTEXT — MILD]: Patient may have mild ME/CFS. Mild patients "
                "often show the greatest day-to-day variability and 'boom and bust' cycling "
                "is particularly prominent. Energy pacing and staying within the energy "
                "envelope is critical even for mild patients who appear functional."
            )
        else:
            severity_note = (
                "\n[Note]: User may have milder ME/CFS. Acknowledge that good days and bad days "
                "are part of the condition; caution against overdoing activity on good days "
                "as this can trigger crashes (boom and bust pattern)."
            )

    focus_block = "\n".join(focus_lines) or "No specific symptom emphasis detected."
    if severity_note:
        focus_block += severity_note

    # ── Symptom intake questionnaire additions (Patient Mode only) ───────
    intake_prompt = ""
    if not is_clinician and focus["diagnosis_ask"]:
        intake_prompt = (
            "\n\nIf the user has not yet described their symptoms fully, you may ask ONE of "
            "these screening questions (do not ask all at once):\n"
            "- Social function: 'Has ME/CFS substantially reduced "
            "your ability to participate in social activities or maintain relationships, even "
            "on days when physical symptoms seem manageable?'\n"
            "- Crash pattern (operationalised PEM): 'Do you experience episodes where your "
            "activity level drops dramatically — needing to spend most of the day resting — "
            "for two or more days following physical or mental exertion, even if the activity "
            "seemed minor at the time?'"
        )

    # ── Mode-specific instructions ───────────────────────────────────────
    if is_clinician:
        instructions = (
            "Instructions:\n"
            "1. Use clinical terminology appropriate for a specialist audience.\n"
            "2. Cite ALL relevant guidelines with inline [N] markers — do not omit any source "
            "that addresses the question.\n"
            "3. If retrieved guidelines AGREE on a point, cite all of them: e.g. [1][3][5].\n"
            "4. If retrieved guidelines DISAGREE, you MUST flag the conflict explicitly: "
            "'[Source A] recommends X [1], but [Source B] does not recommend this [3].' "
            "This is clinically critical — never suppress a guideline conflict.\n"
            "5. Include differential diagnosis, investigation pathways, or red flags where relevant.\n"
            "6. Reference specific criteria (NICE NG206, IOM/NAM 2015, CCC 2003, ICC 2012) by name.\n"
            "7. For mechanistic queries, draw on genomic/pathway evidence in the evidence block.\n"
            "8. Structure with clinical headings if the response covers multiple aspects.\n"
            "9. If retrieved evidence does not cover a specific clinical point, supplement with "
            "established clinical knowledge — do NOT add a citation for knowledge-only points.\n"
            "10. If evidence is conflicting across guidelines, state the conflict explicitly."
        )
    else:
        instructions = (
            "Instructions:\n"
            "1. Answer in plain English with inline citations like [1], [2] wherever the retrieved evidence supports a claim.\n"
            "2. Prioritise the retrieved guideline evidence. Where the evidence covers a point, use it and cite it.\n"
            "3. If the retrieved evidence does not cover a specific point, supplement with your clinical knowledge — but do NOT add a citation for that point.\n"
            "4. Avoid sounding diagnostic.\n"
            "5. Respond only to what the user asked.\n"
            "6. If different guidelines say different things about this topic, "
            "state the difference plainly: e.g. 'Some guidelines say X [1], "
            "while others say Y [3].'"
        )

    conflict_note = detect_conflicts(query, guideline_rows)

    user_content = (
        f"Query: {query}\n\n"
        f"Context notes:\n{focus_block}\n\n"
        f"Guideline evidence:\n{evidence}"
        f"{conflict_note}\n\n"
        f"{instructions}"
        f"{intake_prompt}"
    )

    system_prompt = SYSTEM_PROMPTS.get(mode, PATIENT_SYSTEM_PROMPT)
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
