"""M2-4b — bge-reranker-v2-m3 cross-encoder reranker (local, in-process, offline).

Reorders the matter-pre-filtered candidates from M2-4 by scoring (question, chunk
text) pairs with the bge-reranker-v2-m3 cross-encoder (D-16). It runs as a LOCAL
in-process model loaded via transformers + Torch (already present from Docling) —
NOT via Ollama, which does not serve cross-encoder rerankers (D-36). It does not
replace the D-18 hard pre-filter; it only reorders the already-filtered set.

Weights are fetched once from HuggingFace (the approved one-time fetch); after that
the model loads fully offline. The revision is pinned (RERANKER_REVISION) — like an
embedder change, a reranker change alters results and forces a re-measure.

Scope (M2-4b): rerank only. No answering LLM (M2-5), span verification (M2-6), or
HTTP surface (M2-7).
"""

import os

RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
RERANKER_REVISION = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"

_MODEL = None
_TOKENIZER = None


def _load():
    """Load and cache the cross-encoder once. Offline unless an explicit fetch opt-in."""
    global _MODEL, _TOKENIZER
    if _MODEL is not None:
        return _MODEL, _TOKENIZER
    # Loopback-only default: serve weights from the local HF cache, no hub check.
    if os.environ.get("DOCLING_ALLOW_MODEL_FETCH") != "1":
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    _TOKENIZER = AutoTokenizer.from_pretrained(RERANKER_MODEL, revision=RERANKER_REVISION)
    _MODEL = AutoModelForSequenceClassification.from_pretrained(
        RERANKER_MODEL, revision=RERANKER_REVISION
    )
    _MODEL.eval()
    torch.set_grad_enabled(False)
    return _MODEL, _TOKENIZER


def score(question, texts):
    """Cross-encoder relevance logits for (question, text) pairs. Higher = more relevant."""
    if not texts:
        return []
    import torch

    model, tokenizer = _load()
    pairs = [[question, t] for t in texts]
    with torch.no_grad():
        inputs = tokenizer(
            pairs, padding=True, truncation=True, return_tensors="pt", max_length=512
        )
        logits = model(**inputs).logits.view(-1).float()
    return logits.tolist()


def rerank(question, candidates, top_k=None):
    """Reorder candidates by cross-encoder score (desc); return top_k. Adds rerank_score."""
    if not candidates:
        return []
    scores = score(question, [c["text"] for c in candidates])
    ranked = sorted(
        ({**c, "rerank_score": s} for c, s in zip(candidates, scores)),
        key=lambda c: c["rerank_score"],
        reverse=True,
    )
    return ranked[:top_k] if top_k is not None else ranked
