#!/usr/bin/env python3
"""
test_conflict_detection.py  (25 test cases)
============================================
Offline tests for the inter-guideline conflict registry
(conflict_registry.detect_conflicts), covering the four registered
conflict zones (GET, CBT, diagnosis_criteria, disease_name) plus a set
of negative cases (no false positives on scope-irrelevant queries).

Usage:
    python test_conflict_detection.py
"""

from conflict_registry import detect_conflicts


def rows(*gids):
    return [{"guideline_id": g, "conflict_topics": [], "text": ""} for g in gids]


PASS = FAIL = 0


def test(name, query, gids, expect_conflict=None, expect_agreement=None, expect_empty=False):
    global PASS, FAIL
    result = detect_conflicts(query, rows(*gids))
    ok = True
    msgs = []
    if expect_empty and result != "":
        ok = False
        msgs.append(f"Expected empty, got: {result[:80]}")
    if expect_conflict and f"GUIDELINE CONFLICT on '{expect_conflict}'" not in result:
        ok = False
        msgs.append(f"Missing CONFLICT on '{expect_conflict}'")
    if expect_conflict and "MUST explicitly flag" not in result:
        ok = False
        msgs.append("Missing 'MUST explicitly flag'")
    if expect_agreement and f"GUIDELINE AGREEMENT on '{expect_agreement}'" not in result:
        ok = False
        msgs.append(f"Missing AGREEMENT on '{expect_agreement}'")
    if ok:
        PASS += 1
    else:
        FAIL += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    for m in msgs:
        print(f"        -> {m}")


print("=" * 65)
print("ME/CFS Conflict Detection -- Full Test Suite")
print("=" * 65)

print("\n[1] GET conflicts")
test("GET: NICE+IQWiG -> CONFLICT", "Is graded exercise therapy recommended?",
     ["NICE_NG206", "IQWIG_2023", "IOM_NAM_2015"], expect_conflict="GET")
test("GET: 'can i exercise' -> CONFLICT", "Can I exercise if I have ME/CFS?",
     ["NICE_NG206", "CCC_2003", "IQWIG_2023"], expect_conflict="GET")
test("GET: 'exercise program' -> CONFLICT", "Should I start an exercise program?",
     ["NICE_NG206", "IQWIG_2023"], expect_conflict="GET")
test("GET: NICE+CCC+ICC+IACFSME (no IQWiG) -> AGREEMENT", "Is graded exercise therapy safe?",
     ["NICE_NG206", "CCC_2003", "ICC_2012", "IACFSME_PRIMER_2014"], expect_agreement="GET")
test("GET: only 1 source -> empty", "What is graded exercise therapy?",
     ["NICE_NG206"], expect_empty=True)

print("\n[2] CBT conflicts")
test("CBT: 'does cbt work' + IQWiG -> CONFLICT", "Does CBT work for ME/CFS?",
     ["NICE_NG206", "IQWIG_2023", "CCC_2003"], expect_conflict="CBT")
test("CBT: 'is cbt helpful' -> CONFLICT", "Is CBT helpful for ME/CFS?",
     ["NICE_NG206", "IQWIG_2023"], expect_conflict="CBT")
test("CBT: 'cognitive behavior' -> CONFLICT", "My doctor recommended cognitive behavior therapy.",
     ["NICE_NG206", "CCC_2003", "IQWIG_2023"], expect_conflict="CBT")
test("CBT: NICE+CCC+IACFSME (no IQWiG) -> AGREEMENT", "What does CBT do for ME/CFS?",
     ["NICE_NG206", "CCC_2003", "IACFSME_PRIMER_2014"], expect_agreement="CBT")
test("CBT: IQWiG only -> empty", "Is CBT a psychological treatment?",
     ["IQWIG_2023"], expect_empty=True)

print("\n[3] Diagnosis criteria conflicts")
test("Diag: 'how is me/cfs diagnosed' -> CONFLICT", "How is ME/CFS diagnosed?",
     ["IOM_NAM_2015", "CCC_2003", "ICC_2012", "NICE_NG206"], expect_conflict="diagnosis_criteria")
test("Diag: 'what criteria' -> CONFLICT", "What criteria are used to diagnose ME/CFS?",
     ["IOM_NAM_2015", "CCC_2003"], expect_conflict="diagnosis_criteria")
test("Diag: 'fukuda' -> CONFLICT", "How does Fukuda compare to newer criteria?",
     ["IOM_NAM_2015", "CCC_2003", "IACFSME_PRIMER_2014"], expect_conflict="diagnosis_criteria")
test("Diag: 'minimum symptoms' -> CONFLICT", "How many symptoms needed for ME/CFS diagnosis?",
     ["IOM_NAM_2015", "NICE_NG206", "CCC_2003"], expect_conflict="diagnosis_criteria")
test("Diag: unrelated -> empty", "What is pacing?",
     ["NICE_NG206", "IOM_NAM_2015"], expect_empty=True)

print("\n[4] Disease name")
test("Name: 'why is it called ME/CFS' -> CONFLICT", "Why is it called ME/CFS and not just CFS?",
     ["ICC_2012", "IOM_NAM_2015", "CCC_2003"], expect_conflict="disease_name")
test("Name: 'difference between me and cfs' -> CONFLICT", "What is the difference between ME and CFS?",
     ["ICC_2012", "CCC_2003", "NICE_NG206"], expect_conflict="disease_name")
test("Name: 'should we call it' -> CONFLICT", "Should we call it ME or CFS?",
     ["ICC_2012", "IOM_NAM_2015", "NICE_NG206"], expect_conflict="disease_name")
test("Name: 'myalgic encephalomyelitis vs' -> CONFLICT", "Myalgic encephalomyelitis vs chronic fatigue syndrome?",
     ["ICC_2012", "CCC_2003", "NICE_NG206"], expect_conflict="disease_name")
test("Name: 'SEID'", "What does SEID mean?",
     ["IOM_NAM_2015", "ICC_2012", "NICE_NG206"], expect_conflict="disease_name")
test("Name: 'what does me stand for' -> CONFLICT", "What does ME stand for in ME/CFS?",
     ["ICC_2012", "CCC_2003"], expect_conflict="disease_name")

print("\n[5] No false positives")
test("Pacing -> empty", "How do I pace myself with ME/CFS?",
     ["NICE_NG206", "IOM_NAM_2015", "CCC_2003", "IQWIG_2023"], expect_empty=True)
test("Sleep -> empty", "Why is my sleep unrefreshing?",
     ["NICE_NG206", "IOM_NAM_2015", "CCC_2003"], expect_empty=True)
test("PEM -> empty", "What is post-exertional malaise?",
     ["NICE_NG206", "IOM_NAM_2015", "CCC_2003", "ICC_2012"], expect_empty=True)
test("Generic fatigue -> empty", "Why am I so tired?",
     ["NICE_NG206", "IOM_NAM_2015"], expect_empty=True)

print()
print("=" * 65)
print(f"Results: {PASS} passed, {FAIL} failed -> {'ALL PASS' if FAIL == 0 else str(FAIL) + ' FAILED'}")
print("=" * 65)

if __name__ == "__main__":
    import sys
    sys.exit(0 if FAIL == 0 else 1)
