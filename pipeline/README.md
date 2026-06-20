# pipeline/ — M2 custom citation-grade pipeline

Self-contained Python project for the Milestone 2-3 custom pipeline (authorized by
**M1-13 PASS, D-33**). Isolated from the M1 turnkey AnythingLLM/Ollama baseline — building
here does not touch M1 state, `documents/`, or `eval/`.

## Scope so far

- **M2-1:** PyMuPDF page-accurate ingestion proof. `extract_pages()` (`ingestion.py`) recovers
  per-page text with correct 1-based page numbers from the 6 page-faithful synthetic PDFs in
  `../documents/synthetic_corpus/pdf/`.
- **M2-2 (this task):** `chunking.py` — Docling structure detection + page/section-aware chunking
  with deterministic SAC. Each chunk carries `{source_filename, matter, document_type, page_number,
  section, char_start, char_end, text, embedding_text, section_detected_by_docling}`. Page numbers
  and char offsets come from the M2-1 substrate (offsets are relative to the chunk's PAGE text, the
  M2-6 span substrate); Docling supplies the section-detection signal, reconciled against the
  reliable `#`/`##` heading markers in the M2-1 text. Matter is derived from
  `../eval/golden_manifest.jsonl`. Chunk output (document text) is written to the git-ignored
  `../documents/synthetic_corpus/chunks/`. No embedding/DB/reranker/LLM/retrieval/API yet
  (M2-3..M2-7, see `../TASKS_M2.md`).

- **M2-3 (this task):** `embed_store.py` — embeds each chunk's `embedding_text` (SAC, D-18), NOT
  the bare text, via the system Ollama `bge-m3` (1024-dim, D-11) at `127.0.0.1:11434`, and stores
  vectors + payload `{source_filename, matter, page_number, section, char_start, char_end, text}`
  in an embedded **LanceDB** table (D-34). text + offsets stay in the payload for the M2-6 span
  check. Store lives under the git-ignored `pipeline/.lancedb/`. Includes a plain-vector-search
  similarity sanity check (no metadata filter — that's M2-4). No reranker/LLM/API.

- **M2-4 (this task):** `retrieval.py` — `retrieve(question, matter=None, top_k=5)`. Embeds the
  question via loopback bge-m3, then (when a `matter` is given) hard-pre-filters LanceDB rows to
  that matter **before** similarity (`prefilter=True`), killing the M1 cross-matter pull. The
  `matter` value is validated against the store's known matters (allowlist) before it touches the
  filter — no raw-text injection. `matter=None` is an explicit search-all. No reranker (M2-4b),
  LLM (M2-5), span verification (M2-6), or API (M2-7).

- **M2-4b (this task):** `reranker.py` — `bge-reranker-v2-m3` cross-encoder (D-16), loaded locally
  in-process via `transformers` + Torch (already present; **not** Ollama — it can't serve
  cross-encoder rerankers, D-36). `retrieve(..., rerank=True)` pulls `candidate_k` matter-pre-filtered
  candidates and reorders them by `(question, chunk.text)` cross-encoder score; it never reintroduces
  another matter. Pinned revision `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e` (a reranker change alters
  results — pin alongside D-11). Loads offline after the one-time HF fetch. Measured lift on the 6-doc
  corpus: **neutral** (baseline MRR 0.855 / rank@1 48/63 vs reranked 0.849 / 46/63) — the pre-filter+SAC
  baseline is already strong here; the reranker doesn't regress and is expected to matter more at
  production scale. No LLM (M2-5), span verification (M2-6), or API (M2-7).

- **M2-5 (this task):** `answering.py` — `answer(question, matter=None)`. Hand-rolled (no LlamaIndex,
  D-37): pulls the matter-filtered top-k (`rerank=False`), assembles a labeled context block
  (`[chunk: Ck | document | page | section]`), applies the CE_PLAN §10 grounded-answer + refusal
  prompt, calls `qwen3:14b` on loopback Ollama (`think:false`, `<think>` stripped), and returns
  `{answer_text, citations:[{filename,page,chunk_id}], grounding_chunks:[{chunk_id, source_filename,
  page_number, char_start, char_end, text}]}`. Citations are parsed from the model's §10 tags AND by
  mapping quoted spans back to the grounding chunk that contains them (so a citation can't carry an
  invented page/file). The grounding offsets are the M2-6 substrate. Refusal (D-30) returns the exact
  sentence and cites nothing. No mechanical span verification (M2-6), reranker, or API yet.

- **M2-6 (this task — the keystone):** `verifier.py` — mechanical span-level citation verification
  (D-19). For each claim the answer asserts, the cited span is checked (no LLM) against the offsets of
  the chunk it points to: a claim verifies iff the **normalized** span (M2-1/M2-2 contract: collapse
  whitespace, `-\n`→`-` keep hyphen, drop quotes, lowercase) is a substring of the cited chunk's text;
  the match is mapped back to **page char offsets**. Claims that don't overlap a retrieved chunk are
  **rejected and surfaced** in `rejected_claims` (never silently dropped). Displayed filename + page are
  **chunk-derived** (D-38 — the model's asserted page is never trusted; M2-5 `_parse_citations` was
  fixed). `answer()` now returns `citations` (verified, with `char_start/char_end` page offsets) +
  `rejected_claims`. This delivers the verifiable **page+span** citation M1 proved impossible. No
  FastAPI/eval-run yet.

### Egress / offline default

`chunking.py` forces `HF_HUB_OFFLINE=1` / `TRANSFORMERS_OFFLINE=1` so Docling serves its layout
models from the local cache and a conversion makes **zero egress** (project safety rule #4). The
**one-time** model fetch on a fresh machine is an explicit opt-in: run that first conversion with
`DOCLING_ALLOW_MODEL_FETCH=1`. After the cache is warm, `chunk_corpus()` reads the per-doc
structure cache (`chunks/.docling_headers.json`) and does not invoke Docling at all.

## Setup

```sh
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt   # PyMuPDF only (pinned)
```

## Run the tests (stdlib unittest — no test-framework dependency)

```sh
./.venv/bin/python -m unittest discover -s tests -v
```

The M2-1 span-on-page test reads ground truth from `../eval/golden_manifest.jsonl` and asserts every
present-fact `verbatim_span` is recoverable on its manifest `page_number`. The M2-2 chunking test
asserts each present-fact span resolves to exactly one chunk on the right page with bounding offsets.
Document bodies and chunk outputs stay git-ignored (D-28); only code + tests here are committable.
