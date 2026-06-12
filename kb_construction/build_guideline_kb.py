#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_guideline_kb_full.py
==========================
Fully automated, complete-content ingestion for the ME/CFS guideline KB.

Sources and strategies
----------------------
1. NICE NG206          — direct PDF download (official NICE URL)
2. IOM/NAM 2015 report — full PDF from National Academies Press (free, no login)
3. CDC ME/CFS site     — recursive crawl of ALL /me-cfs/ sub-pages
4. NCBI Bookshelf      — deep recursive crawl of every chapter in NBK274235
5. CDC toolkit PDFs    — direct download of all known toolkit PDFs

Run
---
    python build_guideline_kb_full.py --kb_dir ./kb

Output
------
    kb/guidelines_chunks.jsonl   — all chunks, deduplicated
    kb/guidelines_raw/           — raw downloaded files
    kb/guidelines_text/          — extracted plain text per source
    kb/crawl_report.json         — per-source stats for auditing
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from collections import defaultdict
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader


# ═══════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

REQUEST_TIMEOUT = 60
CRAWL_DELAY    = 1.2   # seconds between requests (polite crawling)
MAX_PAGES      = 300   # safety ceiling per source


# ═══════════════════════════════════════════════════════════════════
# Source definitions
# ═══════════════════════════════════════════════════════════════════

SOURCES = [
    # ── 1. NICE NG206 full PDF ──────────────────────────────────
    {
        "guideline_id": "NICE_NG206",
        "title": "NICE guideline NG206: ME/CFS diagnosis and management",
        "authority": "NICE",
        "priority": 5,
        "tags": ["guideline", "diagnosis", "management", "pem", "fatigue", "sleep", "cognition"],
        "strategy": "pdf",
        "url": (
            "https://www.nice.org.uk/guidance/ng206/resources/"
            "myalgic-encephalomyelitis-or-encephalopathychronic-fatigue-syndrome-"
            "diagnosis-and-management-pdf-66143718094021"
        ),
    },

    # ── 2. IOM/NAM 2015 — crawl all NCBI Bookshelf chapters ─────
    # NAP blocks automated PDF download (returns HTML). Crawl NCBI instead.
    # Chapter NBK IDs are hardcoded from the book TOC as reliable seeds.
    {
        "guideline_id": "IOM_NAM_2015",
        "title": "Beyond ME/CFS: Redefining an Illness (IOM/NAM 2015 full report)",
        "authority": "IOM/NAM",
        "priority": 5,
        "tags": ["report", "criteria", "diagnosis", "pem", "fatigue", "sleep", "cognition", "orthostatic"],
        "strategy": "crawl",
        "seed_url": "https://www.ncbi.nlm.nih.gov/books/NBK274235/",
        "crawl_domain": "https://www.ncbi.nlm.nih.gov",
        "crawl_prefix": "/books/NBK",
        "filter_fn": "ncbi_book_filter",
        "extra_seeds": [
            "https://www.ncbi.nlm.nih.gov/books/NBK274316/",
            "https://www.ncbi.nlm.nih.gov/books/NBK274322/",
            "https://www.ncbi.nlm.nih.gov/books/NBK274323/",
            "https://www.ncbi.nlm.nih.gov/books/NBK274324/",
            "https://www.ncbi.nlm.nih.gov/books/NBK274325/",
            "https://www.ncbi.nlm.nih.gov/books/NBK274326/",
            "https://www.ncbi.nlm.nih.gov/books/NBK274327/",
            "https://www.ncbi.nlm.nih.gov/books/NBK274328/",
            "https://www.ncbi.nlm.nih.gov/books/NBK274329/",
            "https://www.ncbi.nlm.nih.gov/books/NBK274330/",
            "https://www.ncbi.nlm.nih.gov/books/NBK274331/",
            "https://www.ncbi.nlm.nih.gov/books/NBK274332/",
        ],
    },

    # ── 3. CDC ME/CFS — full recursive crawl ────────────────────
    {
        "guideline_id": "CDC_MECFS_FULL",
        "title": "CDC: ME/CFS — complete site",
        "authority": "CDC",
        "priority": 4,
        "tags": ["clinical", "overview", "diagnosis", "management", "fatigue", "pem", "orthostatic"],
        "strategy": "crawl",
        "seed_url": "https://www.cdc.gov/me-cfs/index.html",
        "crawl_domain": "https://www.cdc.gov",
        # Allow any path under /me-cfs/
        "crawl_prefix": "/me-cfs/",
        # Also follow /me-cfs/hcp/ nested sub-directories
        "extra_seeds": [
            "https://www.cdc.gov/me-cfs/hcp/index.html",
            "https://www.cdc.gov/me-cfs/hcp/diagnosis/index.html",
            "https://www.cdc.gov/me-cfs/hcp/clinical-overview/index.html",
            "https://www.cdc.gov/me-cfs/management/index.html",
            "https://www.cdc.gov/me-cfs/hcp/toolkit/index.html",
        ],
    },

    # (IOM NCBI chapters merged into IOM_NAM_2015 above)

    # ── 4. CDC toolkit PDFs (confirmed working URLs) ─────────────
    {
        "guideline_id": "CDC_TOOLKIT_PDFS",
        "title": "CDC: ME/CFS Toolkit PDFs",
        "authority": "CDC",
        "priority": 4,
        "tags": ["symptoms", "fatigue", "pem", "sleep", "brain fog", "pain", "toolkit"],
        "strategy": "pdf_list",
        "urls": [
            # Only the what-is-mecfs PDF is still at the original path.
            # The others were removed from CDC's site; their content is now
            # embedded in the crawled HCP pages (CDC_MECFS_FULL).
            "https://www.cdc.gov/me-cfs/pdfs/toolkit/what-is-mecfs_508.pdf",
        ],
    },
]


# ═══════════════════════════════════════════════════════════════════
# HTTP helpers
# ═══════════════════════════════════════════════════════════════════

def get_with_retry(url: str, retries: int = 3, **kwargs) -> requests.Response:
    """GET with exponential back-off."""
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            if attempt == retries - 1:
                raise
            wait = 2 ** attempt
            print(f"    [RETRY {attempt+1}] {url} — {exc} — waiting {wait}s")
            time.sleep(wait)


def download_file(url: str, dest: str) -> bool:
    """Download binary file, return True on success."""
    try:
        resp = get_with_retry(url, stream=True)
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(65536):
                f.write(chunk)
        size_kb = os.path.getsize(dest) // 1024
        print(f"    [DL] {url} → {dest}  ({size_kb} KB)")
        return True
    except Exception as exc:
        print(f"    [WARN] download failed: {url} — {exc}")
        return False


# ═══════════════════════════════════════════════════════════════════
# Text extraction
# ═══════════════════════════════════════════════════════════════════

def extract_pdf_text(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    pages: List[str] = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")
    return clean_text("\n\n".join(pages))


def soup_to_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript", "header", "footer",
                      "nav", "aside", "form", "button"]):
        tag.decompose()
    body = soup.find("main") or soup.find("article") or soup.body or soup
    return clean_text(body.get_text("\n", strip=True))


def fetch_page_text(url: str) -> str:
    resp = get_with_retry(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    return soup_to_text(soup)


# ═══════════════════════════════════════════════════════════════════
# Crawlers
# ═══════════════════════════════════════════════════════════════════

def _normalise_url(url: str) -> str:
    """Strip fragment and trailing slash for dedup purposes."""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or "/"
    return parsed._replace(fragment="", path=path, query="").geturl()


def _is_within_prefix(url: str, domain: str, prefix: str) -> bool:
    parsed = urlparse(url)
    netloc_ok = parsed.netloc == urlparse(domain).netloc or not parsed.netloc
    path_ok   = parsed.path.startswith(prefix)
    # Reject non-HTML resources
    bad_exts  = (".pdf", ".zip", ".xls", ".xlsx", ".ppt", ".pptx",
                 ".png", ".jpg", ".jpeg", ".gif", ".svg", ".css", ".js")
    ext_ok    = not any(parsed.path.lower().endswith(e) for e in bad_exts)
    return netloc_ok and path_ok and ext_ok


def crawl_site(
    seed_url: str,
    domain: str,
    prefix: str,
    extra_seeds: Optional[List[str]] = None,
    max_pages: int = MAX_PAGES,
    page_filter=None,   # optional callable(url) -> bool
) -> str:
    """
    BFS crawl from seed_url.  Only follows links within domain+prefix.
    Returns concatenated text of all pages.
    """
    queue: List[str] = [seed_url] + (extra_seeds or [])
    visited: Set[str] = set()
    all_texts: List[str] = []
    fetched = 0

    while queue and fetched < max_pages:
        raw_url = queue.pop(0)
        url = _normalise_url(raw_url)

        if url in visited:
            continue
        visited.add(url)

        if page_filter and not page_filter(url):
            continue

        try:
            resp = get_with_retry(url)
            soup = BeautifulSoup(resp.text, "html.parser")

            # Extract text
            text = soup_to_text(soup)
            if text and len(text.split()) > 30:
                all_texts.append(f"\n\n### PAGE: {url}\n\n{text}")
                fetched += 1
                print(f"    [CRAWL {fetched:3d}] {url}  ({len(text.split())} words)")

            # Discover links
            for a in soup.find_all("a", href=True):
                href = a["href"].split("#")[0].split("?")[0]
                if not href:
                    continue
                full = _normalise_url(urljoin(url, href))
                if (full not in visited
                        and _is_within_prefix(full, domain, prefix)):
                    queue.append(full)

            time.sleep(CRAWL_DELAY)

        except Exception as exc:
            print(f"    [WARN] {url} — {exc}")

    print(f"    [CRAWL DONE] {fetched} pages fetched")
    return clean_text("\n\n".join(all_texts))


def crawl_ncbi_book(seed_url: str, domain: str, extra_seeds: List[str] = None) -> str:
    """
    NCBI Bookshelf crawler.

    Strategy:
    1. Collect allowed NBK IDs from:
       a) The extra_seeds list (hardcoded chapter URLs in SOURCES)
       b) Any NBK links found anywhere on the seed page (full-page scan)
    2. Crawl every allowed chapter URL, discovering more NBK links as we go
       but only following ones in the allowed set.
    """
    allowed_nbk: Set[str] = set()

    # Collect NBK IDs from hardcoded extra_seeds
    for s in (extra_seeds or []):
        m = re.search(r"/(NBK\d+)", s)
        if m:
            allowed_nbk.add(m.group(1))

    # Always include the seed itself
    m = re.search(r"/(NBK\d+)", seed_url)
    if m:
        allowed_nbk.add(m.group(1))

    # Scan the seed page for any additional NBK links (full page, not just TOC div)
    print(f"    [NCBI] scanning seed page for chapter IDs: {seed_url}")
    try:
        resp = get_with_retry(seed_url)
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True):
            m2 = re.search(r"/(NBK\d+)", a["href"])
            if m2:
                allowed_nbk.add(m2.group(1))
    except Exception as exc:
        print(f"    [WARN] seed page scan failed: {exc}")

    print(f"    [NCBI] total allowed chapter IDs: {len(allowed_nbk)} — {sorted(allowed_nbk)[:15]}")

    # Build all seed URLs to crawl
    all_seeds = [seed_url] + [
        f"https://{urlparse(domain).netloc}/books/{nbk}/"
        for nbk in sorted(allowed_nbk)
    ]

    def ncbi_filter(url: str) -> bool:
        m3 = re.search(r"/(NBK\d+)", url)
        if not m3:
            return False
        return m3.group(1) in allowed_nbk

    return crawl_site(
        seed_url=seed_url,
        domain=domain,
        prefix="/books/NBK",
        extra_seeds=all_seeds[1:],
        max_pages=MAX_PAGES,
        page_filter=ncbi_filter,
    )


# ═══════════════════════════════════════════════════════════════════
# Text cleaning
# ═══════════════════════════════════════════════════════════════════

def clean_text(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ═══════════════════════════════════════════════════════════════════
# Chunking
# ═══════════════════════════════════════════════════════════════════

def sentence_split(text: str) -> List[str]:
    text = re.sub(r"[ \t]+", " ", text).strip()
    parts = re.split(r'(?<=[\.\?\!])\s+(?=[A-Z0-9"\'])', text)
    return [p.strip() for p in parts if p.strip()]


def chunk_text(
    text: str,
    max_words: int = 120,
    min_words: int = 25,
    overlap: int = 1,
) -> List[str]:
    sents = sentence_split(text)
    if not sents:
        return []

    chunks, cur, cur_w = [], [], 0
    for sent in sents:
        sw = len(sent.split())
        if cur and cur_w + sw > max_words:
            chunk = " ".join(cur).strip()
            if len(chunk.split()) >= min_words:
                chunks.append(chunk)
            cur = cur[-overlap:] if overlap else []
            cur_w = sum(len(x.split()) for x in cur)
        cur.append(sent)
        cur_w += sw

    if cur:
        chunk = " ".join(cur).strip()
        if len(chunk.split()) >= min_words or not chunks:
            chunks.append(chunk)

    return chunks


def detect_section(block: str) -> str:
    for line in block.splitlines()[:8]:
        line = line.strip()
        if 4 < len(line.split()) <= 14 and len(line) <= 120:
            if re.search(
                r"(diagnosis|criteria|symptom|assessment|management|"
                r"post.exertional|orthostatic|sleep|cognitive|fatigue|"
                r"pain|function|activity|overview|chapter|section)",
                line, re.I
            ):
                return line
    return "General"


def infer_tags(text: str, base_tags: List[str]) -> List[str]:
    t = text.lower()
    tags = set(base_tags)
    kw_map = {
        "fatigue":    ["fatigue", "tired", "exhaustion"],
        "pem":        ["post-exertional", "pem", "crash", "after exertion"],
        "sleep":      ["unrefreshing sleep", "sleep disturbance"],
        "cognition":  ["cognitive", "brain fog", "memory", "concentration"],
        "orthostatic":["orthostatic", "lightheaded", "dizziness", "standing", "pots"],
        "pain":       ["pain", "headache", "muscle pain"],
        "diagnosis":  ["diagnosis", "diagnostic", "criteria"],
        "management": ["management", "care", "monitoring"],
    }
    for tag, kws in kw_map.items():
        if any(kw in t for kw in kws):
            tags.add(tag)
    return sorted(tags)


BAD_PATTERNS = [
    "all rights reserved", "notice of rights", "yellow card scheme",
    "local commissioners", "your responsibility", "recent activity",
    "see all", "see reviews", "turn off", "turn on",
    "skip to main content", "page last reviewed", "page last updated",
    "cookie", "javascript", "404", "page not found",
]


def is_bad_chunk(text: str) -> bool:
    tl = text.lower().strip()
    if len(text.split()) < 15:
        return True
    if any(p in tl for p in BAD_PATTERNS):
        return True
    upper = sum(1 for l in text.splitlines()
                if l.strip().isupper() and len(l.strip()) > 3)
    if upper >= 5:
        return True
    return False


def sha1(text: str) -> str:
    return hashlib.sha1(text.encode()).hexdigest()[:16]


def build_chunks(meta: Dict, raw_text: str) -> List[Dict]:
    raw_text = clean_text(raw_text)
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", raw_text) if p.strip()]

    # Merge short paragraphs into ≤220-word blocks
    blocks, temp, tw = [], [], 0
    for p in paragraphs:
        pw = len(p.split())
        if temp and tw + pw > 220:
            blocks.append("\n\n".join(temp))
            temp, tw = [p], pw
        else:
            temp.append(p)
            tw += pw
    if temp:
        blocks.append("\n\n".join(temp))

    chunks: List[Dict] = []
    seen: Set[str] = set()
    idx = 1

    for block in blocks:
        section = detect_section(block)
        for ch in chunk_text(block):
            if is_bad_chunk(ch):
                continue
            h = sha1(ch)
            if h in seen:
                continue
            seen.add(h)
            chunks.append({
                "chunk_id":    f"{meta['guideline_id']}_{idx:04d}",
                "guideline_id": meta["guideline_id"],
                "title":       meta["title"],
                "authority":   meta["authority"],
                "section":     section,
                "text":        ch,
                "url":         meta.get("url", meta.get("seed_url", "")),
                "priority":    meta.get("priority", 3),
                "tags":        infer_tags(ch, meta.get("tags", [])),
                "word_count":  len(ch.split()),
                "hash":        h,
            })
            idx += 1

    return chunks


# ═══════════════════════════════════════════════════════════════════
# Per-strategy ingestion
# ═══════════════════════════════════════════════════════════════════

def ingest_pdf(src: Dict, raw_dir: str) -> str:
    gid = src["guideline_id"]
    pdf_path = os.path.join(raw_dir, f"{gid}.pdf")
    if not os.path.exists(pdf_path):
        ok = download_file(src["url"], pdf_path)
        if not ok:
            # try fallback
            fallback = src.get("url_fallback")
            if fallback:
                print(f"    [INFO] trying fallback URL …")
                ok = download_file(fallback, pdf_path)
            if not ok:
                return ""
    return extract_pdf_text(pdf_path)


def ingest_pdf_list(src: Dict, raw_dir: str) -> str:
    gid = src["guideline_id"]
    all_texts: List[str] = []
    for i, url in enumerate(src["urls"]):
        fname = os.path.join(raw_dir, f"{gid}_{i:02d}.pdf")
        if not os.path.exists(fname):
            ok = download_file(url, fname)
            if not ok:
                continue
        try:
            text = extract_pdf_text(fname)
            if text:
                all_texts.append(f"### SOURCE: {url}\n\n{text}")
                print(f"    [PDF] extracted {len(text.split())} words from {fname}")
        except Exception as exc:
            print(f"    [WARN] PDF extract failed: {fname} — {exc}")
        time.sleep(0.5)
    return clean_text("\n\n".join(all_texts))


def ingest_crawl(src: Dict) -> str:
    if src.get("filter_fn") == "ncbi_book_filter":
        return crawl_ncbi_book(
            seed_url=src["seed_url"],
            domain=src["crawl_domain"],
            extra_seeds=src.get("extra_seeds", []),
        )
    return crawl_site(
        seed_url=src["seed_url"],
        domain=src["crawl_domain"],
        prefix=src["crawl_prefix"],
        extra_seeds=src.get("extra_seeds", []),
    )


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

def write_jsonl(records: List[Dict], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def deduplicate(chunks: List[Dict]) -> List[Dict]:
    seen: Set[str] = set()
    out: List[Dict] = []
    for ch in chunks:
        if ch["hash"] not in seen:
            seen.add(ch["hash"])
            out.append(ch)
    return out


def main() -> None:
    global CRAWL_DELAY, MAX_PAGES

    parser = argparse.ArgumentParser(description="Build complete ME/CFS guideline KB")
    parser.add_argument("--kb_dir", required=True, help="Output directory")
    parser.add_argument("--crawl_delay", type=float, default=CRAWL_DELAY,
                        help="Seconds between requests (default 1.2)")
    parser.add_argument("--max_pages", type=int, default=MAX_PAGES,
                        help="Max pages per crawled source (default 300)")
    args = parser.parse_args()

    CRAWL_DELAY = args.crawl_delay
    MAX_PAGES   = args.max_pages

    raw_dir  = os.path.join(args.kb_dir, "guidelines_raw")
    text_dir = os.path.join(args.kb_dir, "guidelines_text")
    os.makedirs(raw_dir,  exist_ok=True)
    os.makedirs(text_dir, exist_ok=True)

    all_chunks: List[Dict] = []
    report: Dict = {}

    for src in SOURCES:
        gid = src["guideline_id"]
        print(f"\n{'═'*60}")
        print(f"  {gid}  [{src['strategy']}]")
        print(f"{'═'*60}")

        try:
            strategy = src["strategy"]

            if strategy == "pdf":
                raw_text = ingest_pdf(src, raw_dir)

            elif strategy == "pdf_list":
                raw_text = ingest_pdf_list(src, raw_dir)

            elif strategy == "crawl":
                raw_text = ingest_crawl(src)

            else:
                raise ValueError(f"Unknown strategy: {strategy}")

            if not raw_text.strip():
                print(f"  [WARN] no text extracted for {gid}")
                report[gid] = {"words": 0, "chunks": 0, "status": "empty"}
                continue

            # Save raw text for inspection
            txt_path = os.path.join(text_dir, f"{gid}.txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(raw_text)

            word_count = len(raw_text.split())
            print(f"  [TEXT] {word_count:,} words extracted")

            chunks = build_chunks(src, raw_text)
            all_chunks.extend(chunks)

            report[gid] = {
                "words":  word_count,
                "chunks": len(chunks),
                "status": "ok",
            }
            print(f"  [CHUNKS] {len(chunks)} chunks built for {gid}")

        except Exception as exc:
            print(f"  [ERROR] {gid}: {exc}")
            import traceback; traceback.print_exc()
            report[gid] = {"words": 0, "chunks": 0, "status": f"error: {exc}"}

    # Global deduplication
    before = len(all_chunks)
    all_chunks = deduplicate(all_chunks)
    after = len(all_chunks)
    print(f"\n[DEDUP] {before} → {after} chunks ({before - after} duplicates removed)")

    # Write outputs
    out_jsonl = os.path.join(args.kb_dir, "guidelines_chunks.jsonl")
    write_jsonl(all_chunks, out_jsonl)

    report_path = os.path.join(args.kb_dir, "crawl_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    # Summary
    print(f"\n{'═'*60}")
    print(f"  DONE")
    print(f"{'═'*60}")
    print(f"  Output  : {out_jsonl}")
    print(f"  Report  : {report_path}")
    print(f"  Total chunks: {after}")
    print()
    by_source: Dict[str, int] = defaultdict(int)
    for ch in all_chunks:
        by_source[ch["guideline_id"]] += 1
    for gid, n in sorted(by_source.items()):
        status = report.get(gid, {}).get("status", "?")
        words  = report.get(gid, {}).get("words", 0)
        print(f"    {gid:<30s}  {n:>4d} chunks   ({words:>7,} words)  [{status}]")


if __name__ == "__main__":
    main()
