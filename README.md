# ARCagent

This repository contains the core methodology code for ARCagent, an
adaptive retrieval calibration clinical question-answering agent for
ME/CFS, accompanying the paper. It is a cleaned, minimal
subset of the project's codebase: raw PDFs, crawled guideline text,
analysis outputs, logs, and benchmark result files have been removed.
The scripts here implement the methodology described in the paper;
they require a populated `kb/guidelines_chunks.jsonl` (produced by
`kb_construction/build_guideline_kb.py` plus
`kb_construction/genomic_kb.py`) to run end to end.

## Structure

```
kb_construction/
    build_guideline_kb.py   Crawls and chunks the eight guideline sources
                            into kb/guidelines_chunks.jsonl (Section 3.1).
    retag_kb.py             Retroactive tagging pass that scans chunk text
                            for GET/CBT/PEM/orthostatic/conflict terminology
                            to correct under-tagged chunks (Section 4.1).
    genomic_kb.py           Curated genomic/pathway evidence chunks
                            (Section 3.2), appended to the guideline KB.

agent/
    retrieval.py            BM25 + rule-boosted conflict-aware retrieval
                            with per-source diversity cap (Section 4.2).
    conflict_registry.py    Inter-guideline conflict registry: stances per
                            guideline on GET, CBT, diagnosis_criteria, and
                            disease_name, with conflict/agreement detection
                            (Section 3.1, 4.2).
    response_generation.py Dual-mode (patient / clinician) prompt
                            construction with severity-stratified response
                            logic (Section 4.3).

eval/
    test_conflict_detection.py
                            25 offline test cases covering the four
                            registered conflict zones and a set of
                            negative (no-false-positive) queries
                            (Section 6, Conflict Detection Test).
```

## Running the conflict-registry tests

```
cd eval
python test_conflict_detection.py
```

## Building the knowledge base

```
cd kb_construction
python build_guideline_kb.py --kb_dir ./kb
python -c "from genomic_kb import build_genomic_jsonl; build_genomic_jsonl('./kb/guidelines_chunks.jsonl')"
python retag_kb.py --kb_dir ./kb
```

## Running retrieval

```python
from agent.retrieval import GuidelineRetriever, format_evidence_block

retriever = GuidelineRetriever("./kb/guidelines_chunks.jsonl")
results = retriever.search("Is graded exercise therapy still recommended for ME/CFS?", top_k=5)
print(format_evidence_block(results))
```
