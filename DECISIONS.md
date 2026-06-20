# DECISIONS.md — Decisions already made

> Locked decisions carried over from `CE_PLAN.md` (finalized 2026-06-19, revised against the
> Manus AI Technical Validation Report). Section references point back into `CE_PLAN.md`.
> Changing any of these requires an explicit, recorded re-decision.

## Scope and safety

- **D-1 — Product is a cited-retrieval assistant, not an AI lawyer and not an autonomous agent.**
  Grounded search/summarize over the attorney's own docs; no advice, no actions. (CE_PLAN §1, §3)
- **D-2 — Retrieval is architecturally separated from action-taking.** The answering agent has no
  action tools and no network egress in v1. (CE_PLAN §3 principle #12)
- **D-3 — Dev uses fake/sanitized/public documents only;** real data is touched only at Milestone 6,
  onsite, on attorney-owned hardware, after written approval. (CE_PLAN §4 rule 1, §14)
- **D-4 — Local-only data-flow invariant.** No document bytes, embeddings, prompts, or answers leave
  the machine in confidential mode. Loopback binding only; no public port exposure. (CE_PLAN §4)
- **D-5 — Human verification is mandatory, not optional.** Every answer carries a citation and the
  "verify against source / not legal advice" footer. (CE_PLAN §10, §15)
- **D-28 — Synthetic pilot source documents live under ignored `documents/` paths; tracked `eval/`
  files may contain schemas, templates, and metadata but not document bodies.** Every document-like
  file — even synthetic/fake/sanitized pilot documents — lives under the git-ignored `documents/`
  tree (use `documents/synthetic_corpus/`), preserving the invariant that **document data is never
  committable by default**. The `eval/` tree is tracked and holds only the manifest schema,
  templates, and ground-truth metadata (`fact_id`, page, section, short `verbatim_span` snippets
  drawn from synthetic docs only, expected-absent topics, notes) — never a full source-document
  body and never any real client text. This supersedes the working-tree proposal to author the
  corpus under an unignored `corpus/` path, which would have made synthetic documents committable by
  default. (CE_PLAN §4 rule 1, §7.1; `.gitignore`)

## Sequencing

- **D-6 — Turnkey pilot first, before any custom code or capex.** Milestone 1 (Ollama +
  AnythingLLM) must prove citation accuracy and not-found refusal as the go/no-go gate. (CE_PLAN §14,
  §17 Task 0)
- **D-7 — Custom citation-grade build is deferred to Milestones 2–3,** only after M1 passes.
  (CE_PLAN §14)

## M1 measurement decisions (turnkey pilot)

- **D-29 — M1 citation accuracy is scored at FILENAME level, not page level (turnkey limitation;
  owner-approved 2026-06-19).** Empirically (M1-7c), AnythingLLM 1.14.1's desktop PDF parser flattens
  every page into one blob and emits **empty chunk metadata (no page field)** — so verifiable
  page-level citation is **mechanically impossible on the turnkey stack**, even from page-faithful
  PDFs (page breaks confirmed correct; parser is the bottleneck). Therefore M1 measures what the
  turnkey stack can prove: **answer-correctness + filename grounding + DRM right-doc/right-matter +
  not-found refusal.** `page_match` and exact-`verbatim_span` overlap are **dropped from mechanical
  M1 scoring** (page/section remain informational / optional human-read). **The product page-level bar
  is NOT lowered** — verifiable **page + mechanical span** citation is reassigned to **M2-3** (Docling
  page metadata + mechanical span verification), which is exactly where CE_PLAN already places the
  mechanical overlap check. So the M1 page-level miss is a **go/no-go input** (turnkey insufficient for
  the citation bar → the M2-3 custom build is justified), not a silent pass. Encoded in
  `eval/TEST_PLAN.md` §3.1/§4. (CE_PLAN §2 "filename + page/section … mechanically overlaps", §14,
  D-7, D-19)
- **D-30 — M1 not-found refusal is scored on substance, not exact wording (owner-approved).** The
  refusal safety gate passes when the system **declines + cites nothing**; the exact CE_PLAN §10 / D-5
  sentence ("I could not find this in the documents.") is **pinned as the product string** via the
  `m1-golden` workspace prompt and tracked as a separate UX flag `refusal_wording_exact` — a fixable
  UX check, never scored as a hallucination. **Refinement (owner-approved 2026-06-20):** the gate is
  scoped to the **absent topic** — NF passes iff it asserts no substantive answer to the *asked,
  absent* thing AND cites nothing *for it*; an accurate quote about a **different, real** clause is
  **logged as a quality note, not failed**. Because query mode **always** returns a `sources[]` array
  (retrieved chunks) even on refusals, scoring uses the citation the **answer asserts**, not raw
  `sources[]`. Encoded in `eval/TEST_PLAN.md` §3.2. (CE_PLAN §10, D-5)
- **D-31 — M1-10 air-gap (SC-6) is verified by egress monitoring, not physical disconnect
  (owner-approved 2026-06-20).** The full M1-10 run executes with networking **on** while a monitor
  (`lsof`/`nettop`/pktap) runs throughout and proves **zero non-loopback / zero document-bearing
  egress** — exactly CE_PLAN §2 SC-6's "network monitor confirms zero outbound carrying document
  content." Rationale: an AI-driven run needs the network, the corpus is synthetic, and monitoring is
  the CE_PLAN-specified proof. **Supersedes the earlier M1-EH "networking OFF" framing for M1-10
  only;** physical NIC-off air-gap remains the standard for **M6 real-data** work. (CE_PLAN §2 SC-6,
  §11)

- **D-32 — Present-fact `filename_match` is scored via AnythingLLM's returned `sources[]` citation
  panel (owner-approved 2026-06-20).** `filename_match` = the record's `.pdf` appears in the system's
  returned sources/citations (the mechanism by which the turnkey product surfaces citations) — the
  answer prose need not name the file. This is how both the Builder and the independent Tester graded
  M1-10; the **63/63 = 100%** present-fact metric stands on this reading. Asymmetry is intentional: NF
  "cites nothing" is scored on the **answer-asserted** citation, ignoring the always-present
  `sources[]` (D-30). (TEST_PLAN §3.1)
- **D-33 — M1-13 GO/NO-GO = PASS (filename level); M2-3 build authorized (owner, 2026-06-20).** The
  turnkey pilot met all four §4 gates on the synthetic corpus — citation **100%** (63/63, filename
  level per D-29/D-32), **0** fabricated, not-found refusal **100%** (9/9, D-30), **DRM 2/2** — under
  egress-monitored SC-6 (D-31). This is the CE_PLAN §14 go/no-go gate: turnkey local RAG + grounding +
  refusal are **validated**, and verifiable page+span citation is **proven impossible** on the turnkey
  stack → the **M2-3 custom pipeline is authorized** (FastAPI + LlamaIndex + Docling + Qdrant/LanceDB +
  reranker + mechanical span verification, D-13..D-20). **No production hardware purchase yet** (M4-5,
  after M2-3 validates). Carry-forward build inputs: verifiable page+span (D-19), DRM
  metadata-filter+reranker (D-18/D-16), latency tuning. See `BUILDER_STATE.md`. (CE_PLAN §14, D-6, D-7)

- **D-34 — M2 vector store = LanceDB (embedded), owner-chosen 2026-06-20.** Resolves D-14's
  Qdrant-primary / LanceDB-alternative in favor of **LanceDB** for the M2 build: embedded/serverless
  (no Docker, no server process), already proven on this machine (AnythingLLM's `m1-golden` ran on
  LanceDB), and sufficient metadata pre-filtering for single-tenant matter-scoping at D-26 scale.
  **Qdrant drops out of the deployment** (D-20); revisit only if M2-4 filtering or production scale
  demands it. Each chunk's payload carries `{source_filename, matter, page_number, section, char_start,
  char_end}` + chunk text (for M2-6); embed the **`embedding_text`** (SAC-prefixed, D-18). The LanceDB
  store contains document text → **git-ignored** (D-28). (CE_PLAN §6.4, D-14, D-20)

- **D-35 — M2 retrieval matter-scoping = explicit `matter` param (hard pre-filter); reranker
  sequenced separately (owner, 2026-06-20).** Matter-scoping is supplied as an **explicit `matter`
  filter param — no NLP inference from the question.** When provided, LanceDB **hard-pre-filters** rows
  to that matter **before** similarity (filter-then-search); absent → an explicit "search all matters."
  Rationale: inferring the matter from free text is the exact "right clause, wrong client" failure the
  system must prevent, and a solo attorney works within a known matter context; M2-3 showed SAC alone
  doesn't stop matter-agnostic cross-matter pulls. The **`bge-reranker-v2-m3` reranker (D-16) is
  sequenced as a separate step M2-4b** (its own owner-gated model install) after the proven-required
  pre-filter, so its lift can be isolated/measured — D-16 (reranker planned) is honored, just
  sequenced. (D-18, D-16, CE_PLAN §10)

- **D-36 — Reranker runs as a LOCAL in-process cross-encoder, not via Ollama (2026-06-20).**
  `bge-reranker-v2-m3` (D-16) is loaded directly via FlagEmbedding / sentence-transformers (Torch,
  already present from Docling) — **Ollama does not serve cross-encoder rerankers natively.** Weights
  are fetched once from HuggingFace (one-time, no document content); set HF/transformers **offline**
  after the fetch to prove air-gapped reranking. The reranker **reorders the matter-pre-filtered
  candidates** (M2-4) — it does not replace the D-18 hard pre-filter. Pin its revision/digest alongside
  the D-11 model pins and **measure its lift** vs the pre-filter baseline before relying on it. (D-16,
  D-35, CE_PLAN §10)
  **Refinement (2026-06-20, M2-4b measured):** the reranker **defaults OFF** (`rerank=False`) —
  measured **neutral lift** on the 6-doc corpus (ΔMRR ~-0.006, rank@1 48→46) does not justify its
  latency; it is **opt-in via `rerank=True`** and re-evaluated at real scale. **M2-5 answering builds
  on the `rerank=False` base path.** The pinned `RERANKER_REVISION` (in `reranker.py`) joins the
  central model-pin list alongside `qwen3:14b=bdbd181c33f2` and `bge-m3=790764642607` (D-11); a
  revision change forces re-eval.

- **D-37 — M2 answering/orchestration is hand-rolled; LlamaIndex dropped (supersedes the RAG part of
  D-13; owner, 2026-06-20).** The pipeline is built directly (PyMuPDF ingest → chunk + SAC → LanceDB →
  matter-filtered retrieval), **not** via LlamaIndex, for **full transparency of the
  claim→chunk→offset citation path** that mechanical span verification (D-19 / M2-6) requires — and
  because the M1 failure was an opaque framework's citation handling. M2-5 answering is a thin
  function: assemble matter-filtered (`rerank=False`) context with explicit per-chunk source labels →
  CE_PLAN §10 grounded + cite-every-claim + refusal prompt → `qwen3:14b` on system Ollama (D-11) →
  return the answer + the grounding chunk IDs/offsets. **This supersedes the "LlamaIndex (RAG)" portion
  of D-13;** the **FastAPI HTTP surface (D-13) still stands** for M2-7. (CE_PLAN §6.6, §10, D-13, D-19)

- **D-38 — Displayed citations are CHUNK-DERIVED, never model-asserted (2026-06-20, M2-5 Reviewer
  bug).** The filename + page shown to the user are taken from the **matched chunk's metadata**
  (`grounding_chunks[chunk_id].source_filename` / `.page_number`), **not** from the model's prose. The
  model's asserted citation is only a *pointer* to a chunk; the system replaces it with the chunk's
  verified filename+page, and (M2-6) mechanically verifies the cited span overlaps that chunk's
  offsets. **A model-asserted page is never trusted or displayed.** Fixes the M2-5 `_parse_citations`
  structured-tag branch (which emitted the model's page) — a **precondition of M2-6**. (D-19, D-29;
  M1 lesson: model-asserted pages were confidently wrong and unverifiable.)

- **D-39 — M2-8 re-instates the page+span citation bar that D-29 relaxed for the turnkey stack
  (2026-06-20).** Now that the custom pipeline delivers chunk-derived pages (D-38) + mechanical span
  verification (D-19, M2-6), the **M2-8 golden re-run scores at the original CE_PLAN §2/§11 bar**:
  present-fact citation = answer conveys fact **AND** chunk-derived `filename_match` **AND** `page_match`
  (chunk-derived page == manifest `page_number`) **AND** the cited span **mechanically verifies**
  against a retrieved chunk. **Displayed fabricated/mis-paged citations = hard-zero** — they must be
  rejected into `rejected_claims`, never shown (mechanically enforced by M2-6, not prompt-trusted). NF
  refusal stays the D-30 substance gate; DRM stays right-matter. Encoded in `eval/TEST_PLAN.md` §6; the
  M1 §3/§4 filename-level definition (D-29) remains the historical M1 record. (CE_PLAN §2, §11, D-19,
  D-29, D-38)

## Stack — pilot (Milestone 1)

- **D-8 — Model runtime: Ollama** (pilot and production). OpenAI-compatible local API, Metal
  acceleration, serves both chat and embedding models. (CE_PLAN §6.1)
- **D-9 — Pilot UI: AnythingLLM.** Chosen over Open WebUI for lowest hallucination (6%) and the best
  out-of-the-box filename + page citations in the May 2026 benchmark. (CE_PLAN §6.2, §16 Q3)
- **D-10 — Chat model: `qwen3:14b`** (alt: Mistral Small 3.1 24B). Disciplined grounded RAG that
  degrades gracefully when evidence is missing. (CE_PLAN §6/§12, §16)
- **D-11 — Embedding model: `bge-m3` via Ollama,** chosen for native hybrid dense + sparse support;
  to be validated against our own legal golden set (not MTEB rank) before locking. Pin the id; a
  change forces a full re-index. (CE_PLAN §6.5)
- **D-12 — Pilot deployment: native macOS apps, no Docker.** (CE_PLAN §6.8)

## Stack — production (deferred, recorded for context; do NOT build in M1)

- **D-13 — Orchestration: FastAPI (HTTP surface) + LlamaIndex (RAG).** (CE_PLAN §6.6)
- **D-14 — Vector DB: Qdrant** (best metadata filtering for matter scoping); LanceDB is the
  embedded server-less alternative. (CE_PLAN §6.4)
- **D-15 — Parsing/OCR: Docling + PyMuPDF, Tesseract fallback.** PyMuPDF routes text-vs-image; born-
  digital via PyMuPDF normalized through Docling; image-only via Tesseract. (CE_PLAN §6.3)
- **D-16 — Reranker: `bge-reranker-v2-m3`,** planned (not "only if measured"). (CE_PLAN §10)
- **D-17 — Storage: lifecycle folders** (`inbox`/`processed`/`failed`/`originals`) + SQLite metadata
  catalog mirrored into vector payloads; originals read-only. (CE_PLAN §6.7, §7)
- **D-18 — Anti-DRM: metadata-filter-before-similarity + Summary-Augmented Chunking (SAC).** Prevents
  "right clause, wrong client" retrieval. (CE_PLAN §9, §10)
- **D-19 — Mechanical span-level citation verification in code.** A cited span must mechanically
  overlap an actually-retrieved chunk's offsets, or the claim is rejected before display. The prompt
  alone is not trusted. (CE_PLAN §10)
- **D-20 — Production deployment: Docker Compose** (Qdrant + FastAPI/LlamaIndex + thin UI), Ollama on
  host. Qdrant drops out if LanceDB is chosen. (CE_PLAN §6.8, §13)

## Hardware

- **D-21 — Pilot runs on the in-hand MacBook Pro 14" M4 Pro, 24GB unified.** No production hardware
  purchase until SC-1..SC-7 pass and the attorney has seen the demo. (CE_PLAN §12)
- **D-22 — Production target (recommended): Mac Studio M4 Max, 64–128GB unified** (Option A
  appliance); CUDA path (RTX 5070 Ti/5080/5090) only if latency/scale demands it. Do not buy on spec.
  (CE_PLAN §12)

## Resolved project questions (CE_PLAN §16)

- **D-23 — Single solo attorney, single-tenant v1.** Multi-user is a later concern.
- **D-24 — PDF first (born-digital and scanned), then DOCX, then TXT.** Scanned PDFs are first-class.
- **D-25 — No remote access in v1** (local/air-gapped); Tailscale only revisited later with written
  approval.
- **D-26 — First production corpus: a few thousand documents** (drives the 14B–32B / 16–32GB sweet
  spot; 70B unnecessary).
- **D-27 — Support model: ongoing managed** (Jake owns updates/backups/model refreshes on a defined
  cadence). Exact cadence + response SLA still to pin down with the attorney.

## Still open / to confirm

- **O-1 — `bge-m3` vs `qwen3-embedding`** final choice pending evaluation against the legal golden
  set. (CE_PLAN §6.5) — relevant from Milestone 2 onward.
- **O-2 — Support cadence + response-time SLA** numbers, to confirm with the attorney. (CE_PLAN §16
  Q10)
