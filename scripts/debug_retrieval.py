#!/usr/bin/env python3
"""Diagnostic script to check ChromaDB for GDPR article coverage and ranking.

Run: uv run python scripts/debug_retrieval.py
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import chromadb

from gdpr_ai.config import settings
from gdpr_ai.knowledge.embeddings import embed_texts

ROOT = Path(__file__).resolve().parents[1]
RAW_ARTICLES = ROOT / "data" / "raw" / "gdpr_articles.json"


def _article_variants(n: str) -> list[str]:
    """Known metadata shapes for article n."""
    return [f"Art. {n}", f"Article {n}"]


def _print_raw_gdpr_overview() -> None:
    """Print article list and lengths from gdpr_articles.json."""
    print("\n=== Step 2: Raw scraped data (data/raw/gdpr_articles.json) ===")
    if not RAW_ARTICLES.exists():
        print(f"MISSING file: {RAW_ARTICLES}")
        return
    raw = RAW_ARTICLES.read_text(encoding="utf-8")
    try:
        data: list[dict[str, Any]] = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}")
        return
    if not data:
        print("File is empty (no articles). Re-run: uv run python scripts/scrape_gdpr.py")
        return
    print(f"Article count: {len(data)}")
    for art in data:
        num = art.get("article_number", "?")
        title = art.get("title", "")
        print(f"  - {num!r} | title={title!r}")
    for want in ("6", "7", "21"):
        found = next((a for a in data if str(a.get("article_number")) == want), None)
        if found:
            t = found.get("text") or ""
            print(f"Art. {want} text length: {len(t)} chars")
        else:
            print(f"Art. {want}: NOT PRESENT in JSON")


def _similarity_from_distance(dist: float, space: str) -> float:
    """Map Chroma distance to an interpretable similarity score."""
    if space == "cosine":
        return 1.0 - float(dist)
    return 1.0 / (1.0 + float(dist))


def main() -> None:
    print("=== Step 1: ChromaDB ===")
    chroma_dir = settings.chroma_path
    if not chroma_dir.exists():
        print(f"MISSING Chroma path: {chroma_dir}")
        _print_raw_gdpr_overview()
        return

    client = chromadb.PersistentClient(path=str(chroma_dir))
    try:
        coll = client.get_collection(settings.chroma_collection)
    except Exception as exc:  # noqa: BLE001
        print(f"Cannot open collection {settings.chroma_collection!r}: {exc}")
        _print_raw_gdpr_overview()
        return

    total = coll.count()
    print(f"Collection: {settings.chroma_collection!r}")
    print(f"Total chunks: {total}")

    meta_space = (coll.metadata or {}).get("hnsw:space", "cosine")
    print(f"HNSW space: {meta_space}")

    for label in ["6", "7", "21"]:
        variants = _article_variants(label)
        found_any = False
        for av in variants:
            got = coll.get(where={"article_number": av}, include=["documents", "metadatas"])
            ids = got.get("ids") or []
            if not ids:
                continue
            found_any = True
            print(f"\nFound article_number={av!r} — {len(ids)} chunk(s)")
            for cid, doc, meta in zip(
                ids,
                got.get("documents") or [],
                got.get("metadatas") or [],
                strict=False,
            ):
                preview = (doc or "")[:200].replace("\n", " ")
                print(f"  id={cid} meta={meta}")
                print(f"  text[:200]={preview!r}")
        if not found_any:
            print(f"\nMISSING — Art. {label} not in ChromaDB (no metadata match)")

    def run_query(label: str, q: str, top_k: int) -> None:
        print(f"\n--- Similarity search: {label!r} (top_k={top_k}) ---")
        q_vec = embed_texts(settings.embedding_model, [q])[0]
        raw = coll.query(
            query_embeddings=[q_vec],
            n_results=min(top_k, max(1, total)),
            include=["documents", "metadatas", "distances"],
        )
        ids = raw["ids"][0]
        docs = raw["documents"][0]
        metas = raw["metadatas"][0]
        dists = raw["distances"][0]
        for rank, (cid, doc, meta, dist) in enumerate(
            zip(ids, docs, metas, dists, strict=True),
            start=1,
        ):
            sim = _similarity_from_distance(float(dist), str(meta_space))
            an = (meta or {}).get("article_number", "")
            src = (meta or {}).get("source", "")
            prev = (doc or "")[:100].replace("\n", " ")
            print(
                f"  {rank:2d}  sim~{sim:.4f}  dist={float(dist):.4f}  "
                f"source={src!r} article={an!r}"
            )
            print(f"      {prev!r}")

    run_query("marketing / consent", "marketing emails without consent", 30)
    run_query("lawful basis", "lawful basis for processing personal data consent", 15)

    _print_raw_gdpr_overview()

    print("\n=== Step 3: Chunking defaults (scripts use gdpr_ai.knowledge.chunk_split) ===")
    print("max_tokens=512, overlap_tokens=64 (BGE tokenizer)")
    print("GDPR articles use paragraph-aware pieces + title prefix (see knowledge/gdpr_text.py)")


if __name__ == "__main__":
    main()
