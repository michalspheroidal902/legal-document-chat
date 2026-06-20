"""M2-4 — Metadata-filter-before-similarity retrieval with an explicit matter param.

Matter-scoping is supplied as an explicit ``matter`` filter (D-35) — never inferred
from the question. When a matter is given, LanceDB hard-pre-filters rows to that
matter BEFORE similarity (``prefilter=True``), so the M1 "right clause, wrong
client" cross-matter pull cannot happen; when ``matter is None`` it is an explicit
search-all. The matter value is validated against the store's known matters (an
allowlist) before it touches the filter string, so raw text is never interpolated.

Scope (M2-4): retrieval only. No reranker (M2-4b), answering LLM (M2-5), span
verification (M2-6), or HTTP surface (M2-7).
"""

from pathlib import Path

from embed_store import embed_texts, open_table

_DEFAULT_DB = Path(__file__).resolve().parent / ".lancedb"
_PAYLOAD_FIELDS = (
    "source_filename", "matter", "page_number", "section", "char_start", "char_end", "text",
)


def known_matters(db_path=None):
    """Distinct matter values present in the store (the matter allowlist)."""
    table = open_table(str(db_path or _DEFAULT_DB))
    return sorted({r["matter"] for r in table.to_arrow().to_pylist()})


def retrieve(question, matter=None, top_k=5, db_path=None, rerank=False, candidate_k=20):
    """Return the top-k chunks for ``question``, optionally hard-scoped to ``matter``.

    matter is None -> explicit search-all. matter set -> validated against the
    store's known matters, then a hard pre-filter applied before similarity.

    rerank=True (M2-4b): pull ``candidate_k`` matter-pre-filtered candidates, reorder
    them with the local bge-reranker-v2-m3 cross-encoder, and return the top-k. The
    reranker only reorders the already-filtered set — it never reintroduces another
    matter (the D-18 hard pre-filter is upstream and intact).
    """
    table = open_table(str(db_path or _DEFAULT_DB))
    query_vec = embed_texts([question])[0]
    search = table.search(query_vec)

    if matter is not None:
        allowed = {r["matter"] for r in table.to_arrow().to_pylist()}
        if matter not in allowed:
            raise ValueError(f"unknown matter (not in store): {matter!r}")
        # Value is from the allowlist, not raw user text; double-quote defensively.
        escaped = matter.replace("'", "''")
        search = search.where(f"matter = '{escaped}'", prefilter=True)

    limit = max(top_k, candidate_k) if rerank else top_k
    rows = search.limit(limit).to_arrow().to_pylist()
    candidates = [{k: r[k] for k in (*_PAYLOAD_FIELDS, "_distance") if k in r} for r in rows]

    if rerank:
        from reranker import rerank as _rerank  # lazy: keep the base path torch-free
        return _rerank(question, candidates, top_k=top_k)
    return candidates[:top_k]
