#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
genomic_kb.py — Genomically Informed RAG Knowledge Base
========================================================
Curated pathway-level summaries from ME/CFS multi-omics literature.
These chunks extend the guideline knowledge base so the RAG system can
respond to mechanistic queries (e.g. "Why do I feel worse after exercise?")
with biologically grounded evidence.

Sources drawn from:
- Hanson et al. (PNAS) — metabolic profiling
- Germain et al. — mitochondrial dysfunction
- Hornig et al. — immune profiling
- Davis et al. — ME/CFS multi-omics review
- Síthigh & Bhatt — neuroinflammation review
- Tronstad et al. — transcriptomic ME/CFS subtypes
- Recursion / You+ME collaborative findings

Usage
-----
    from genomic_kb import GENOMIC_CHUNKS, build_genomic_jsonl

    # Append to existing KB:
    build_genomic_jsonl("./kb/guidelines_chunks.jsonl")

    # Or load chunks directly:
    chunks = GENOMIC_CHUNKS
"""

from __future__ import annotations

import json
import os
from typing import List, Dict

# ---------------------------------------------------------------------------
# Curated genomic / pathway evidence chunks
# ---------------------------------------------------------------------------

GENOMIC_CHUNKS: List[Dict] = [

    # ── 1. Mitochondrial dysfunction & energy metabolism ──────────────────
    {
        "chunk_id":    "GEN_MITO_001",
        "guideline_id":"genomic_evidence",
        "title":       "ME/CFS: Mitochondrial Dysfunction and Energy Metabolism",
        "authority":   "Multi-omics literature (Germain et al.; Hanson et al.)",
        "section":     "Biological Pathways — Mitochondrial",
        "url":         "https://doi.org/REDACTED",
        "source_type": "genomic",
        "priority":    5,
        "tags": [
            "mitochondria", "energy", "oxidative phosphorylation",
            "ATP", "metabolism", "PEM", "post-exertional malaise",
            "why worse after exercise",
        ],
        "text": (
            "Mitochondrial dysfunction is a consistently implicated biological mechanism in ME/CFS, "
            "providing a molecular basis for the cardinal symptom of post-exertional malaise (PEM). "
            "Metabolomic profiling (Hanson et al., PNAS) identified a hypometabolic "
            "signature in ME/CFS patients — reduced amino acid catabolism, disrupted fatty acid "
            "oxidation, and impaired TCA cycle intermediates — consistent with defective mitochondrial "
            "energy production under metabolic demand. Germain et al. demonstrated significantly "
            "reduced mitochondrial respiratory capacity in ME/CFS peripheral blood mononuclear cells "
            "(PBMCs), with Complex I activity substantially lower than in healthy controls. "
            "This impairment in oxidative phosphorylation means that even modest physical or cognitive "
            "exertion can deplete cellular ATP reserves faster than they can be replenished aerobically, "
            "forcing a switch to less efficient anaerobic metabolism. The resulting lactate accumulation "
            "and ATP depletion are proposed molecular drivers of the post-exertional symptom exacerbation "
            "characterizing PEM, typically peaking in the days following activity. "
            "Clinical implication: energy pacing strategies should be grounded in this bioenergetic "
            "constraint — the 'energy envelope' concept maps directly onto mitochondrial ATP ceiling."
        ),
    },

    # ── 2. NK cell dysfunction & immune exhaustion ────────────────────────
    {
        "chunk_id":    "GEN_IMMUNE_001",
        "guideline_id":"genomic_evidence",
        "title":       "ME/CFS: NK Cell Dysfunction and T Cell Exhaustion",
        "authority":   "Multi-omics literature (Hornig et al.; Brenu et al.; Moneghetti et al.)",
        "section":     "Biological Pathways — Immune",
        "url":         "https://doi.org/REDACTED",
        "source_type": "genomic",
        "priority":    5,
        "tags": [
            "NK cell", "natural killer", "T cell", "immune", "cytotoxicity",
            "exhaustion", "cytokine", "interferon", "immune dysfunction",
        ],
        "text": (
            "Immune dysregulation is among the most replicated biological findings in ME/CFS. "
            "Natural killer (NK) cell dysfunction — reduced cytotoxic activity despite normal or "
            "elevated cell counts — has been demonstrated across multiple independent cohorts "
            "(Brenu et al.; Moneghetti et al.). NK cell cytotoxicity is typically "
            "substantially lower in ME/CFS patients versus matched healthy controls, impairing viral "
            "immune surveillance and potentially explaining the high prevalence of viral triggers "
            "and reactivation patterns. "
            "T cell exhaustion markers (PD-1, TIM-3, LAG-3 upregulation) have been documented in "
            "ME/CFS PBMCs, consistent with chronic immune activation driving an exhausted phenotype "
            "unable to mount or sustain effective immune responses. "
            "Hornig et al. (Science Advances) demonstrated cytokine dysregulation that "
            "differs systematically by illness duration: early-stage ME/CFS shows pro-inflammatory "
            "cytokine elevation (IFN-γ, TNF-α, IL-17A), while late-stage disease shows "
            "immunosuppressive shift — suggesting immune exhaustion as a progressive feature. "
            "Interferon-stimulated gene (ISG) signatures are upregulated in high-severity patients, "
            "pointing toward ongoing innate immune activation. "
            "Clinical implication: immune biomarkers (NK cytotoxicity, ISG score) may serve as "
            "objective severity markers and could stratify patients for targeted interventions."
        ),
    },

    # ── 3. Neuroinflammation & brain metabolism ───────────────────────────
    {
        "chunk_id":    "GEN_NEURO_001",
        "guideline_id":"genomic_evidence",
        "title":       "ME/CFS: Neuroinflammation and Central Nervous System Involvement",
        "authority":   "Multi-omics literature (Nakatomi et al., PET; Younger et al.; Síthigh & Bhatt)",
        "section":     "Biological Pathways — Neurological",
        "url":         "https://doi.org/REDACTED",
        "source_type": "genomic",
        "priority":    5,
        "tags": [
            "neuroinflammation", "brain", "microglia", "cognitive", "brain fog",
            "CNS", "HPA axis", "cortisol", "autonomic", "neural",
        ],
        "text": (
            "Neuroinflammation has emerged as a key biological feature of ME/CFS, supported by "
            "PET imaging, CSF proteomics, and transcriptomic studies. "
            "Nakatomi et al. (Journal of Neuroscience) demonstrated elevated microglial "
            "activation (measured by PET imaging with a microglial-binding tracer) in multiple brain regions including "
            "the cingulate cortex, hippocampus, amygdala, thalamus, and midbrain in ME/CFS "
            "patients versus healthy controls, with regional neuroinflammation correlating "
            "significantly with cognitive fatigue severity. "
            "HPA axis dysregulation — blunted cortisol awakening response and reduced diurnal "
            "cortisol variation — has been documented in many ME/CFS patients, "
            "reflecting disrupted neuroendocrine feedback potentially driven by chronic immune "
            "activation and neuroinflammatory signaling. "
            "CSF proteomic studies have identified elevated neuroinflammatory markers (IL-6, "
            "IL-8, CXCL1) and reduced neurotrophic support (BDNF) in ME/CFS, consistent with "
            "impaired neuronal maintenance in the context of ongoing central inflammation. "
            "This neurobiological substrate provides mechanistic grounding for the cognitive "
            "symptoms (brain fog, memory impairment, slowed processing) that patients report — "
            "these are not psychological phenomena but reflect measurable CNS pathology. "
            "Clinical implication: cognitive symptoms should be taken as seriously as physical "
            "symptoms in assessment and management; cognitive pacing is as important as "
            "physical activity pacing."
        ),
    },

    # ── 4. Autonomic dysfunction & POTS ───────────────────────────────────
    {
        "chunk_id":    "GEN_AUTO_001",
        "guideline_id":"genomic_evidence",
        "title":       "ME/CFS: Autonomic Nervous System Dysfunction and POTS",
        "authority":   "Multi-omics literature (Raj et al.; Barnden et al.; Wirth & Scheibenbogen)",
        "section":     "Biological Pathways — Autonomic",
        "url":         "https://doi.org/REDACTED",
        "source_type": "genomic",
        "priority":    5,
        "tags": [
            "autonomic", "POTS", "dysautonomia", "orthostatic", "heart rate",
            "HRV", "vagal", "sympathetic", "standing", "dizziness", "tachycardia",
        ],
        "text": (
            "Autonomic nervous system dysfunction is present in the majority of ME/CFS patients "
            "and constitutes a primary biological pathway linking multiple symptom domains. "
            "Postural Orthostatic Tachycardia Syndrome (POTS) — defined as a marked heart-rate "
            "increase shortly after standing without orthostatic hypotension — affects a "
            "substantial proportion of ME/CFS patients. Broader autonomic dysfunction (measured by "
            "heart rate variability, tilt-table testing, and quantitative sudomotor testing) is "
            "present in most cohorts. "
            "Barnden et al. demonstrated brainstem abnormalities on structural MRI in "
            "ME/CFS patients, with reduced grey matter in regions controlling autonomic and "
            "interoceptive function (dorsal vagal complex, nucleus tractus solitarius), providing "
            "anatomical substrate for autonomic dysregulation. "
            "Wirth & Scheibenbogen proposed an autoimmune mechanism: autoantibodies "
            "against adrenergic (β2, α1) and muscarinic (M3, M4) receptors have been detected "
            "at elevated levels in ME/CFS, potentially disrupting receptor-mediated autonomic "
            "signaling. This autoimmune hypothesis aligns with the post-infectious onset pattern "
            "and the female predominance of the condition. "
            "Reduced heart rate variability (HRV) — reflecting reduced parasympathetic tone — "
            "correlates with functional impairment severity and may serve as an objective "
            "wearable biomarker of autonomic burden. "
            "Clinical implication: orthostatic symptoms warrant systematic tilt-table or active "
            "stand testing; POTS pharmacotherapy (fludrocortisone, ivabradine, LDN) may provide "
            "symptom relief independent of underlying ME/CFS mechanisms."
        ),
    },

    # ── 5. Transcriptomic subtypes & severity ─────────────────────────────
    {
        "chunk_id":    "GEN_TRANS_001",
        "guideline_id":"genomic_evidence",
        "title":       "ME/CFS: Transcriptomic Subtypes and Severity-Stratified Gene Expression",
        "authority":   "Multi-omics literature (Tronstad et al.; Sweetman et al.; Bhatt et al.)",
        "section":     "Biological Pathways — Transcriptomic",
        "url":         "https://doi.org/REDACTED",
        "source_type": "genomic",
        "priority":    4,
        "tags": [
            "transcriptomic", "gene expression", "RNA-seq", "subtype",
            "severity", "WGCNA", "DEG", "interferon-stimulated gene",
            "NK cell", "oxidative phosphorylation",
        ],
        "text": (
            "Transcriptomic profiling of ME/CFS PBMCs consistently identifies gene expression "
            "patterns that differentiate patients from controls and stratify by severity. "
            "Key convergent findings across RNA-seq studies include: "
            "(1) Upregulation of interferon-stimulated genes (ISGs: IFIT1, IFIT3, MX1, OAS1) "
            "in high-severity patients, reflecting sustained innate immune activation consistent "
            "with antiviral signaling even in the absence of active infection. "
            "(2) Downregulation of oxidative phosphorylation pathway genes (NDUFA, SDHB, COX "
            "subunits) in severe patients, corroborating metabolomic evidence of mitochondrial "
            "dysfunction. "
            "(3) Reduced NK cell and cytotoxic T cell gene signatures (NKG7, GNLY, PRF1, GZMB) "
            "despite preserved or elevated NK cell counts, indicating functional exhaustion "
            "without numerical depletion. "
            "Tronstad et al. used WGCNA to identify co-expressed gene modules correlating "
            "with clinical severity scores — the highest-severity patient cluster showed a "
            "distinctive module combining ISG upregulation and mitochondrial downregulation "
            "not present in lower-severity patients, suggesting a biologically distinct severe "
            "endotype. "
            "Sweetman et al. identified sex-stratified differences in gene expression: "
            "female patients showed stronger interferon pathway activation; male patients showed "
            "greater metabolic dysregulation — consistent with clinical observations of sex "
            "differences in symptom profile. "
            "Clinical implication: transcriptomic signatures may eventually support objective "
            "diagnosis and severity stratification; ISG score and OXPHOS module expression "
            "are candidate biomarkers for future clinical validation."
        ),
    },

    # ── 6. Epigenetics & DNA methylation ─────────────────────────────────
    {
        "chunk_id":    "GEN_EPIGEN_001",
        "guideline_id":"genomic_evidence",
        "title":       "ME/CFS: Epigenetic Modifications and DNA Methylation",
        "authority":   "Multi-omics literature (de Vega et al., EPIC array; Almenar-Pérez et al.)",
        "section":     "Biological Pathways — Epigenetic",
        "url":         "https://doi.org/REDACTED",
        "source_type": "genomic",
        "priority":    4,
        "tags": [
            "epigenetic", "methylation", "EPIC array", "CpG", "DMR",
            "immune", "stress response", "HPA", "onset", "trigger",
        ],
        "text": (
            "Epigenetic studies using Illumina EPIC methylation arrays have identified differentially "
            "methylated regions (DMRs) in ME/CFS patients versus controls, with most DMRs "
            "located in regulatory regions of immune and stress-response genes. "
            "de Vega et al. (PLOS ONE) reported a large number of differentially methylated CpGs in "
            "ME/CFS patients, significantly enriched in pathways related to immune cell "
            "differentiation, T cell signaling, and HPA axis regulation — consistent with "
            "epigenetic programming of immune exhaustion and blunted stress response. "
            "Hypomethylation of glucocorticoid receptor (NR3C1) regulatory elements has been "
            "observed in ME/CFS, consistent with the reduced HPA axis reactivity (blunted "
            "cortisol awakening response) documented in neuroendocrine studies — epigenetic "
            "mechanisms may underlie the chronicity of HPA dysregulation. "
            "Almenar-Pérez et al. identified methylation signatures distinguishing "
            "ME/CFS onset subtypes (post-infectious versus gradual onset), suggesting that "
            "different triggering mechanisms may produce biologically distinguishable epigenetic "
            "fingerprints that persist over the disease course. "
            "The post-COVID ME/CFS overlap: emerging evidence suggests substantial epigenetic "
            "overlap between ME/CFS and post-acute sequelae of SARS-CoV-2 (PASC), with shared "
            "hypomethylation patterns in interferon-response and T cell exhaustion loci. "
            "Clinical implication: epigenetic biomarkers may eventually support stratification "
            "by onset type and provide targets for epigenetic therapies (HDAC inhibitors, "
            "methylation modulators) in precision ME/CFS management."
        ),
    },

    # ── 7. Crash event data — empirical evidence chunk ────────────────────
    {
        "chunk_id":    "GEN_CRASH_001",
        "guideline_id":"empirical_data_evidence",
        "title":       "ME/CFS Crash Events: Quantitative Characterization from Wearable Data",
        "authority":   "Rekeland et al. wearable-data reanalysis (this work)",
        "section":     "Empirical Evidence — Activity Monitoring",
        "url":         "https://doi.org/REDACTED",
        "source_type": "empirical_data",
        "priority":    5,
        "tags": [
            "PEM", "crash", "activity crash", "wearable", "Fitbit", "steps",
            "post-exertional malaise", "energy crash", "activity monitoring",
            "severity", "floor effect", "objective monitoring",
        ],
        "text": (
            "Objective characterization of ME/CFS crash events using continuous wrist-worn "
            "activity-tracker data (Rekeland cohort reanalysis; novel analysis not in the "
            "original publication): "
            ""
            "Crash event definition: a sustained drop in step count below a rolling-median "
            "baseline over several consecutive days. "
            ""
            "Key findings: a meaningful number of crash events were detected across the cohort, "
            "occurring repeatedly per patient over the observation window. "
            "Crash duration was typically a few days. "
            "Crash depth was substantial, with step counts falling well below the "
            "pre-crash rolling baseline across severity groups. "
            "Post-crash recovery was gradual and often incomplete within the observation window. "
            ""
            "Severity paradox (floor effect): Mild patients showed the greatest relative crash "
            "depth, while Severe patients showed a smaller relative crash depth. This is not "
            "because severe patients crash less severely — it reflects a floor effect: severe "
            "patients' baseline step counts are already compressed, leaving limited downward "
            "headroom to trigger a fixed relative threshold. A fixed threshold therefore "
            "underestimates crash frequency in the most severely affected patients. "
            ""
            "Day-to-day variability: Mild patients showed the greatest oscillation between "
            "good and bad days, consistent with the 'boom and bust' pattern. "
            ""
            "Clinical monitoring recommendation: a sustained drop in step count below a "
            "rolling-median baseline can serve as an objective proxy for PEM crash events in "
            "continuous wearable monitoring. Severity-stratified thresholds are recommended "
            "for research applications to maintain equivalent sensitivity across severity strata."
        ),
    },

    # ── 8. GWAS & polygenic risk ──────────────────────────────────────────
    {
        "chunk_id":    "GEN_GWAS_001",
        "guideline_id":"genomic_evidence",
        "title":       "ME/CFS: Genetic Architecture and GWAS Findings",
        "authority":   "Multi-omics literature (Löfgren et al.; Schur et al.; Hill et al.)",
        "section":     "Biological Pathways — Genomic",
        "url":         "https://www.meresearch.org.uk/research/",
        "source_type": "genomic",
        "priority":    3,
        "tags": [
            "GWAS", "genetic", "SNP", "variant", "heritability",
            "polygenic", "HLA", "immune genes", "risk", "familial",
        ],
        "text": (
            "Genetic studies in ME/CFS are limited by small sample sizes relative to other "
            "complex diseases, but emerging evidence suggests meaningful genetic architecture. "
            "Heritability estimates from twin studies indicate a substantial "
            "genetic contribution that is nevertheless not deterministic — consistent with "
            "gene-environment interaction models involving environmental triggers (infection, "
            "stress, trauma) in genetically susceptible individuals. "
            "Early GWAS efforts (Schur et al.; Löfgren et al.) identified nominal "
            "associations in immune-related loci (HLA region, cytokine receptor genes, "
            "complement pathway) and autonomic signaling pathways, though no findings have "
            "reached genome-wide significance in ME/CFS-specific analyses due to underpowering. "
            "Hill et al. (UK Biobank analysis) identified genetic correlations between "
            "ME/CFS and autoimmune conditions (RA, lupus, IBD), depression, and neuroticism — "
            "consistent with shared immune and neuroendocrine genetic architecture rather than "
            "ME/CFS being a purely psychological phenotype. "
            "Polygenic risk scores (PRS) for immune dysregulation traits (inflammatory bowel "
            "disease, thyroid autoimmunity) show modest but significant elevation in ME/CFS "
            "cohorts, supporting the autoimmune-adjacent biological positioning of the condition. "
            "Mendelian randomization analyses suggest that inflammatory cytokine levels "
            "(IL-6, CRP) may have causal relationships with fatigue outcomes — implicating "
            "immune-to-brain signaling in symptom generation. "
            "Note: ME/CFS GWAS is severely underpowered by current standards; much larger "
            "sample sizes are needed for reliable discovery. The You + ME Registry "
            "represents a critical resource for building toward adequate statistical power."
        ),
    },

    # ── 9. Multi-omics integration summary for clinicians ─────────────────
    {
        "chunk_id":    "GEN_SUMMARY_001",
        "guideline_id":"genomic_evidence",
        "title":       "ME/CFS Multi-Omics: Integrated Biological Model Summary",
        "authority":   "Multi-omics review (Davis et al.; Komaroff et al.; Sotzny et al.)",
        "section":     "Biological Pathways — Integrated Model",
        "url":         "https://doi.org/REDACTED",
        "source_type": "genomic",
        "priority":    5,
        "tags": [
            "multi-omics", "biological model", "mechanism", "summary",
            "immune", "mitochondria", "autonomic", "neuroinflammation",
            "integrated", "endotype", "subtype",
        ],
        "text": (
            "The emerging multi-omics consensus positions ME/CFS as a biological condition "
            "with measurable molecular pathology across immune, metabolic, neurological, and "
            "autonomic systems — not a functional somatic or psychosomatic disorder. "
            ""
            "Integrated biological model: "
            "A triggering event (viral infection, immune challenge, trauma) in a genetically "
            "susceptible individual initiates dysregulated immune activation. Persistent "
            "innate immune signaling (elevated ISGs, NK cell dysfunction, cytokine dysregulation) "
            "drives HPA axis dysregulation and autonomic nervous system disruption. Mitochondrial "
            "dysfunction — secondary to immune-metabolic crosstalk or primary mitochondrial "
            "pathology — impairs cellular energy production, creating the bioenergetic ceiling "
            "that underlies PEM. Neuroinflammation (microglial activation, blood-brain barrier "
            "disruption) produces cognitive and central sensitization symptoms. The syndrome "
            "perpetuates through immunological memory, epigenetic programming, and altered "
            "autonomic setpoints. "
            ""
            "Two proposed endotypes (awaiting validation): "
            "Endotype A (post-infectious, younger onset, stronger ISG signature, better NK "
            "reserve): may be more amenable to immunomodulatory approaches. "
            "Endotype B (gradual onset, older age, greater HPA/autonomic involvement, lower "
            "ISG signal): may respond better to autonomic stabilization and HPA support. "
            ""
            "What multi-omics cannot yet do today: no single validated biomarker for clinical "
            "diagnosis; no approved pharmacological treatment based on these mechanisms; all "
            "findings remain research-grade and require clinical translation. "
            "Management remains guideline-grounded (NICE NG206, IOM 2015): pacing, "
            "symptom management, specialist referral. Mechanistic findings inform the 'why' "
            "but not yet the 'what to prescribe'."
        ),
    },
]


# ---------------------------------------------------------------------------
# KB integration functions
# ---------------------------------------------------------------------------

def build_genomic_jsonl(kb_jsonl_path: str) -> int:
    """
    Append genomic chunks to an existing guidelines_chunks.jsonl file.
    Skips chunks whose chunk_id already exists in the file.
    Returns the number of chunks appended.
    """
    # Check existing chunk IDs
    existing_ids: set = set()
    if os.path.exists(kb_jsonl_path):
        with open(kb_jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        row = json.loads(line)
                        existing_ids.add(row.get("chunk_id", ""))
                    except json.JSONDecodeError:
                        pass

    appended = 0
    with open(kb_jsonl_path, "a", encoding="utf-8") as f:
        for chunk in GENOMIC_CHUNKS:
            if chunk["chunk_id"] in existing_ids:
                print(f"  [SKIP] {chunk['chunk_id']} already in KB")
                continue
            # Add word count
            chunk_out = dict(chunk)
            chunk_out["word_count"] = len(chunk["text"].split())
            f.write(json.dumps(chunk_out, ensure_ascii=False) + "\n")
            appended += 1
            print(f"  [ADD]  {chunk['chunk_id']}: {chunk['title'][:60]}")

    return appended


def get_genomic_chunks_as_rows() -> List[Dict]:
    """
    Return genomic chunks as retrieval-ready rows (with sid placeholder).
    Use for in-memory injection without modifying the JSONL file.
    """
    rows = []
    for i, chunk in enumerate(GENOMIC_CHUNKS, start=1):
        row = dict(chunk)
        row["sid"] = str(i)
        row["word_count"] = len(chunk["text"].split())
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# CLI: append to KB
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    kb_path = sys.argv[1] if len(sys.argv) > 1 else "./kb/guidelines_chunks.jsonl"

    if not os.path.exists(kb_path):
        print(f"ERROR: KB file not found: {kb_path}")
        print("Run build_guideline_kb.py first to create the guideline KB.")
        sys.exit(1)

    print(f"Appending genomic chunks to: {kb_path}")
    n = build_genomic_jsonl(kb_path)
    print(f"\nDone. {n} genomic chunk(s) added.")
    print("\nTo verify:")
    print(f"  python -c \"import json; rows=[json.loads(l) for l in open('{kb_path}')]; "
          f"print(f'Total chunks: {{len(rows)}}'); "
          f"print(f'Genomic chunks: {{sum(1 for r in rows if r.get(\\\"source_type\\\")===\\\"genomic\\\")}}')\"")
