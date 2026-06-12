#!/usr/bin/env python3
"""
retag_kb.py
===========
Retroactively adds missing tags to existing KB chunks.

Problem: NICE_NG206, IOM_NAM_2015, CDC_MECFS_FULL chunks lack 'cbt' and 'get'
tags, so they don't get retrieved on CBT/GET queries. This causes:
  - NICE NG206's "do not offer GET/CBT" to be missed
  - Conflict detection to fail (needs NICE in retrieved set)
  - Model to give wrong answers when NICE not retrieved

Fix: Scan all chunks, add missing tags based on text content.

Usage:
    python retag_kb.py --kb_dir ./kb
"""
import argparse, json, re
from collections import Counter

# Expanded keyword map for retroactive tagging
RETAG_RULES = {
    "cbt": [
        "cognitive behav", "CBT", "cognitive therapy",
        "talking therapy", "psychological treatment",
        "psychotherapy", "cognitive retraining",
    ],
    "get": [
        "graded exercise", "GET", "exercise therapy",
        "exercise program", "exercise programme",
        "incremental exercise", "structured exercise",
        "activity program", "activity programme",
    ],
    "pacing": [
        "pacing", "energy envelope", "boom and bust",
        "activity management", "activity budget",
    ],
    "orthostatic": [
        "POTS", "orthostatic", "NMH", "neurally mediated",
        "postural tachycardia", "tilt-table", "dysautonomia",
    ],
    "diagnosis": [
        "diagnostic criteria", "case definition",
        "IOM 2015", "NICE NG206", "CCC 2003",
        "Fukuda", "diagnosis of ME", "diagnose ME",
    ],
    "pem": [
        "post-exertional", "PEM", "post exertional",
        "exertional malaise", "activity crash",
        "boom-and-bust",
    ],
    "sleep": [
        "unrefreshing sleep", "non-restorative", "sleep dysfunction",
        "sleep disturbance",
    ],
    "pain": [
        "myalgia", "widespread pain", "fibromyalgia",
        "headache", "musculoskeletal pain",
    ],
    "immune": [
        "NK cell", "natural killer", "cytokine", "interferon",
        "immune dysfunction", "lymphocyte",
    ],
    "neurological": [
        "brain fog", "cognitive impairment", "neurocognitive",
        "cognitive dysfunction", "encephalomyelitis",
    ],
    "conflict": [
        "however", "in contrast", "differ", "disagree",
        "not recommended", "do not offer", "advise against",
    ],
}

def retag(text: str, existing_tags: list) -> list:
    tags = set(existing_tags)
    tl = text.lower()
    for tag, kws in RETAG_RULES.items():
        if any(kw.lower() in tl for kw in kws):
            tags.add(tag)
    return sorted(tags)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--kb_dir", default="./kb")
    args = p.parse_args()

    path = f"{args.kb_dir}/guidelines_chunks.jsonl"
    rows = []
    with open(path) as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))

    print(f"Loaded {len(rows)} chunks")

    # Count tags before
    tag_counts_before = Counter()
    for row in rows:
        for t in row.get("tags", []):
            tag_counts_before[t] += 1

    # Retag
    changed = 0
    per_source_added = Counter()
    for row in rows:
        old_tags = set(row.get("tags", []))
        new_tags = set(retag(row["text"], list(old_tags)))
        added = new_tags - old_tags
        if added:
            row["tags"] = sorted(new_tags)
            changed += 1
            per_source_added[row["guideline_id"]] += 1

    # Count tags after
    tag_counts_after = Counter()
    for row in rows:
        for t in row.get("tags", []):
            tag_counts_after[t] += 1

    print(f"\nChunks with new tags added: {changed}")
    print("\nBy source:")
    for gid, n in sorted(per_source_added.items(), key=lambda x: -x[1]):
        print(f"  {gid}: {n} chunks retagged")

    print("\nKey tag changes:")
    for tag in ["cbt", "get", "pacing", "orthostatic", "diagnosis", "conflict"]:
        before = tag_counts_before.get(tag, 0)
        after = tag_counts_after.get(tag, 0)
        delta = after - before
        print(f"  '{tag}': {before} → {after} (+{delta})")

    # Write back
    with open(path, "w") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"\nSaved. KB ready — restart agent to reload.")

if __name__ == "__main__":
    main()
