# OSS Evaluation — mining 9 repos for adoptable tools/techniques (2026-06-21)

> Owner-directed deep dive (collaborative session). For EACH repo: shallow-cloned to `/tmp/<repo>`,
> mapped structure, read core source (not READMEs), inventoried deps/techniques, cross-referenced
> against our actual `pipeline/*.py`, flagged concrete adopt/adapt candidates. Run by 9 parallel
> general-purpose agents. **No installs, no code execution** — source-read only. This is a research
> note feeding candidate DECISIONS/M-tasks; nothing here is greenlit until the owner picks threads.

## Our non-negotiables used to judge "fit"
100% local / air-gapped / loopback-only · no cloud APIs · **citation-grade mechanical span
verification (conservative — never false-accepts)** · synthetic data until M6. A technique needing a
cloud call or heavy server is LOW fit unless it has a local/embeddable mode.

---

## Headline finding
**We already installed Docling 2.104, run a full conversion on every doc, and then throw away ~95% of
its output** — we keep only `section_header` strings to confirm our `#`/`##` regex. Turning on
`do_table_structure` (TableFormer) and reading the `ProvenanceItem` (page + bbox + charspan) already
attached to every element closes our **two worst capability gaps — tables/exhibits and bbox-precise
citations — with no new cloud dependency and only a one-time, already-gated local model download.**
Best value/effort/fit ratio of anything found.

---

## Cross-cutting themes (where multiple repos converge)

### A. Tables / exhibits — biggest capability gap (we have ZERO table handling today)
- **Docling TableFormer** (`do_table_structure=True`, default on) → `TableItem` with per-cell
  bbox/page provenance, `export_to_markdown/dataframe/html`, triplet serialization for embedding.
  Offline after one-time model fetch. **Already available in our installed version.** Effort M.
- **RAGFlow** `deepdoc/vision/table_structure_recognizer.py` (ONNX TSR → HTML tables w/ rowspan/colspan
  + caption breadcrumb); the **docx/born-digital HTML-table path is pure-Python (high fit)**, the vision
  TSR is M/L. Effort M (docx) / L (vision).
- **kotaemon** `format_context.py` `table_origin` — per-evidence-type context formatting + table-specific
  QA prompt. ADAPT pattern, S/M.
- Legal value: fee schedules, damages matrices, contract/exhibit schedules currently ingest as garbled
  text. High.

### B. Tabular-review UX — directly matches the stated "UI improvements" priority
- **Tabular_Review** (`jamietso`): rows=documents × columns=questions × cells=cited answers, click-to-
  verify side-by-side viewer, confidence pills, "p.N" citation chips, scroll-to-span, reusable question
  template library, CSV export. ~1,900 LOC React+**cloud Gemini** — **ADAPT the pattern, not the code.**
- Right shape for us: a server-driven `POST /grid {matter, doc_ids[], questions[]}` that fans our
  existing `answer()` (retrieve+answer+**verify**) across the matrix with **bounded** concurrency (not
  their unbounded `Promise.all`), streamed via SSE, rendered in a new static grid page that reuses our
  **own** mechanical span verifier for the highlight. Their cell schema (value/confidence/quote/page/
  reasoning/status) maps ~1:1 onto our citation result — but we upgrade un-verifiable fuzzy-quote
  highlight → our verified spans. Effort: M (endpoint) + L (UI). Ref: `App.tsx::processExtraction`
  379–443, `components/DataGrid.tsx`, `components/VerificationSidebar.tsx`.

### C. Transcripts (owner's net-new gap) — HONEST STATUS: nobody solves this
- **No repo has page:line citation or Q/A-aware transcript chunking.** Confirms the earlier read: it's
  genuinely net-new design.
- Closest skeletons to ADAPT:
  - **RAGFlow `rag/app/qa.py`** — Q/A-pair detection + cross-page answer stitching (by bbox `top`, NOT
    line). Best existing Q/A structure skeleton; page:line must be added by us.
  - **Docling `PageChunker`** — correct one-chunk-per-page boundary for transcripts; combine with
    **PyMuPDF per-line y-coordinates** to derive the `:line`. Docling alone won't give the line number.
- Verdict: still a brainstorm-first design task; these give a partial head start, not a solution.

### D. Structured field / clause extraction (legal value, cheap S-effort wins — all local prompt/data)
- **CUAD 41-clause taxonomy** (`Legal-AI_Project/server/data/questions*.txt`) — ready-to-use contract
  clause question set (Governing Law, Non-Compete, MFN, Change-of-Control, Liability Cap, IP, Audit…).
  Pure data, zero deps. Run each through our existing RAG+LLM+verifier to auto-populate a "contract
  summary" panel. Effort S.
- **THEOLEX `legal_doc_processing`** — "QA-as-extraction" pattern (per-field question banks → ask model
  → merge by score) + **doc-type taxonomy** (~44 filing types: Complaint, Consent Order, DPA, NPA,
  Indictment…) + multi-paraphrase score-merge reliability trick + jurisdiction alias map. **ADAPT
  patterns, don't vendor** (stale 2021, buggy, left-in `pdb`, DistilBERT < our qwen3). Effort S/M.
- **Superwise `Legal_Document_Analyzer_AI`** — legal prompt schema: 5 doc categories + 11-section output
  (Document Type / Key Clauses / Obligations / Parties / Dates / Financial Terms / Risk / **Missing
  Terms** / Compliance) + non-advice disclaimer + non-legal refusal string. **ADAPT the prompt**, graft
  our span-verification (require verbatim quotes per clause). "Missing Terms" (which standard clauses are
  ABSENT) is a useful new angle — but inherently non-citable, present as advisory. Effort S.
- All of these feed our existing LLM + span verifier — they fill the "legal doc typing / clause
  extraction" gap without new infrastructure.

### E. Real-court-PDF robustness (we've only tested SYNTHETIC PDFs — M6 readiness)
- **freelawproject/bankruptcy-parser** — battle-tested on real PACER PDFs. ADAPT 3 techniques into our
  PyMuPDF ingest: (1) **line-geometry "crop above the rule line"** extraction for filled forms
  (`utils.py:45-74`); (2) **font-size/name span filtering** to separate entered data from pre-printed
  labels (`filters.py`); (3) **symbol-font (Wingdings) checkbox normalization** `cid:132`→`[√]`
  (`filters.py:136-147`); plus multi-tolerance retry. PyMuPDF exposes the equivalents
  (`get_drawings()`, `get_text("dict")` w/ bbox+size+font) — **port patterns, don't add pdfplumber/
  PyPDF2 deps.** Grab their 3 real court PDF fixtures as test data. Effort: S–M. Directly de-risks the
  open M6 "real-PDF section detection" carry-forward.

### F. Retrieval / answer-quality refinements (mostly local, mostly S)
- **kotaemon logprob answer-confidence** (`citation_qa.py:274` `qa_score=exp(mean logprob)`) — Ollama
  exposes logprobs; trivial confidence/abstain signal complementing our refusal. ADOPT, S.
- **kotaemon sentence-window retrieval** — index tight chunks, feed wider neighbor window to the LLM;
  our char-offset model already supports storing a window range. ADAPT, S/M. Helps precision + latency.
- **kotaemon fuzzy span highlight** — ONLY as a non-gating UI fallback when our exact verifier finds no
  overlap (never marks "verified"). Keep exact verifier as the gate. ADAPT, S.
- **RAGFlow `rag/app/laws.py`** — hierarchical heading-tree chunking (Article/§/numbered-clause tree
  merge, "Article X:" heading detection, TOC strip). Pure Python, legal-relevant; adapt to emit our
  char offsets. ADAPT, M.
- **RAGFlow RAPTOR** (recursive cluster-summarize tree) for matter-level "summarize the whole matter"
  questions + scale. All-local (sklearn/umap + our Ollama) but marginal at small scale (same reasoning
  that deferred hybrid/RRF). STUDY/DEFER, L.

### G. Ingestion throughput / scale (NOTE: not the <3s answer-latency yellow)
- **Tabular_Review** Docling **MPS (Metal) acceleration** (`AcceleratorDevice.MPS`) — near-free
  ingestion speedup on Apple Silicon for the "thousands of docs" concern. This is **ingestion
  throughput, NOT query first-token latency** (the open G-LAT yellow is answer latency — different
  lever). STUDY, S.

---

## What CONFIRMS our existing choices (don't churn these)
- **Our mechanical span verifier is a genuine competitive advantage.** Every other repo uses weaker
  grounding: RAGFlow LLM-asserted `[ID:n]` (format/range check only, no entailment), kotaemon +
  Tabular_Review fuzzy regex highlight (would false-accept), Superwise/lawyergpt none. Keep it; it's the
  product.
- **Our RRF hybrid is stronger than kotaemon's** (they naively concat dense+lexical with a sentinel
  −1.0 score; real ordering comes only from their reranker — likely a dedup no-op bug).
- **Matter pre-filter + SAC chunking** validated as correct (lawyergpt's no-filter `similarity>0.25`
  would leak across matters; its fixed-rune no-overlap chunking is strictly worse than ours).
- **Hand-rolling (no LlamaIndex/LangChain)** — kotaemon shows the framework-coupling cost we avoided.
- **LanceDB-embedded over Qdrant** — multiple repos run server doc stores (ES/Infinity/pgvector) we
  don't need at our scale.

## Explicitly SKIP
GraphRAG (all backends need API keys/heavy setup; we rejected knowledge-graph) · Qdrant/Milvus/Chroma/
ES/Infinity/pgvector server stores · llama-index/langchain cores · cloud ingestion (Azure DI / Adobe /
Mathpix) · all cloud LLM/embedding paths (Gemini/OpenAI) · web-search retrievers · the bankruptcy-
specific field schemas · PyPDF2/Wand/mlx_vlm dead deps · T5 paraphrase / TextBlob sentiment · the
broken THEOLEX segmentation stub.

## Dependency-cost flags (we keep serving deps lean)
- Docling HybridChunker pulls `transformers` + `semchunk`; CUAD extractive model pulls `torch` +
  `transformers`; spaCy NER auto-downloads a model (must vendor for air-gap). Weigh before adding.
- TableFormer/RAGFlow-ONNX/Docling layout models = one-time HF download then offline — acceptable under
  our existing `DOCLING_ALLOW_MODEL_FETCH` gate, but it IS a fetch (gate it).
- Honest caveat on Docling provenance: Docling's `charspan` indexes into Docling's OWN serialized item
  text, NOT PyMuPDF page text → it does **not** replace our PyMuPDF offsets for the verifier. Keep
  PyMuPDF as offset source-of-truth; add Docling bbox/page as corroborating provenance + UI crop.

---

## Per-repo one-line verdicts
| Repo | Verdict | Best single steal |
|---|---|---|
| docling-project/docling | **ADOPT** (already installed) | TableFormer tables + `ProvenanceItem` bbox/page we already compute |
| infiniflow/ragflow | ADAPT | `laws.py` hierarchical heading-tree chunking; `qa.py` as transcript skeleton; docx HTML tables |
| jamietso/Tabular_Review | ADAPT (pattern) | tabular review-grid UX + multi-doc×question fan-out over our verifier |
| Cinnamon/kotaemon | ADAPT (selective) | logprob answer-confidence; sentence-window retrieval |
| freelawproject/bankruptcy-parser | ADAPT (technique) | line-geometry form-field extraction; font-band filter; checkbox glyph norm |
| THEOLEX/legal_doc_processing | ADAPT (patterns) | QA-as-extraction + doc-type taxonomy + paraphrase-merge |
| OssamaLouati/Legal-AI_Project | ADAPT (data) | CUAD 41-clause taxonomy |
| superwise/Legal_Document_Analyzer_AI | SKIP code / ADAPT prompt | legal 11-section output schema + "Missing Terms" |
| glamboyosa/lawyergpt | SKIP (2 S-steals) | per-page OCR-fallback control flow; auto-title prompt |

---

## Planner's recommended sequencing (for owner greenlight)
1. **Docling tables + provenance harvest (A)** — highest value/effort/fit; already paid the conversion
   cost. → new M-task, brainstorm-light (mostly turning on + reading existing output).
2. **Tabular-review grid (B)** — matches stated UI priority; reuses `answer()`+verifier. → brainstorm
   the UX, then `POST /grid` + static grid page.
3. **Clause-extraction quick win (D)** — CUAD taxonomy + legal prompt schema into a "contract summary"
   panel, span-verified. Cheap, high attorney value.
4. **Transcripts (C)** — separate, brainstorm-first design workstream (page:line + Q/A chunking); these
   repos give only partial skeletons.
5. **Real-PDF robustness (E)** — fold bankruptcy-parser techniques + real fixtures into the M6-readiness
   track.
6. Refinements (F) + MPS ingestion speedup (G) as opportunistic small wins.

_None of this changes the open G-LAT `<3s` answer-latency yellow (different lever). Still owner-gated:
M4-5 hardware, M6 real data._

---

## Tester cross-evaluation reconciliation (2026-06-21)

A second, independent 9-repo deep dive was run in the Tester tab (same repos, same protocol). It
**converged with this note** on all majors (Docling under-use = top finding; tabular grid + transcripts
= the two real new capabilities; our mechanical span verifier is ahead of every repo; most legal repos
are thin cloud demos whose value is data/prompts not code; skip cloud/heavy-infra/frameworks). Net-new
items it surfaced, now folded into the plan:

- **`eyecite` (Free Law Project) — ADD (M-ENRICH small win).** Pure-Python, offline extraction/
  normalization of case + statute citations ("Smith v. Jones, 123 F.3d 456", "42 U.S.C. § 1983") into
  structured metadata → retrieve-by-cited-authority. Genuinely fills the structured-legal-field gap and
  pairs with clause extraction. My agents missed it (it's an FLP *sibling* lib, not inside
  bankruptcy-parser). Low–medium effort.
- **Docling `OcrMac` (native macOS Vision OCR) — STUDY.** Zero model weights, fully offline, faster than
  Tesseract on Apple Silicon. Optional OCR-path swap; only relevant on our Mac dev/target hardware.
- **Streaming token UX (SSE) — Tier-3.** Doesn't lower first-token time but improves *perceived* latency
  (our open yellow). Cheap; fold into a future UI touch.
- **Architectural sharpening — offset-routing (promoted to a decision, D-51):** never mix PyMuPDF and
  Docling char-offsets on the SAME chunk (silently breaks span verification). Pick **one canonical
  extractor per document**: keep the **PyMuPDF fast path for clean born-digital text** (latency), run the
  **heavy Docling path only on tabular/scanned docs**. This is the right framing for T-TBL and supersedes
  a naive "always run Docling" approach.

**Push-backs (where I do NOT fully adopt the Tester's read):**
- **Fuzzy span-verify fallback (kotaemon difflib) must stay STRICTLY NON-GATING.** A `SequenceMatcher`
  match (e.g. 0.85 similarity) is NOT a verbatim span — it may render a "probable source (unverified)" UI
  highlight, but it must **never** enter the verified-citation set or flip a claim to displayed/verified.
  Anything else weakens D-19/D-38's never-false-accept invariant — our core moat. Adopt only as a labeled
  non-gating UI aid.
- **Recall fixes ≠ proven F-026 fix.** Top-k×N-before-rerank (#7a) is a *plausible* fix for F-026
  (page-1 caption not surfaced) — worth testing — but it's a **hypothesis; measure, don't assert**. And
  the fuzzy fallback (#5) would NOT fix F-026 (the chunk was never retrieved — a recall miss, not a
  normalization-drift miss); different failure mode.
- **Prefer logprob answer-confidence over an extra LLM-as-grader call.** Both give a confidence/abstain
  signal; the logprob version (kotaemon `qa_score=exp(mean logprob)`) is ~free and adds no latency,
  whereas an LLM relevance-grader adds a round-trip. Use logprob as primary; LLM-grader only if needed.

**Open fork for the owner — sequencing.** The owner pre-approved **Docling-tables-first** (T-TBL-1, model
fetch + markdown-per-table). The Tester independently argues **clause-checklist-first** (cheapest,
instantly attorney-legible, and most clauses — governing law, non-compete, liability cap, indemnity — are
*prose*, so they do NOT depend on tables; tables matter mainly for financial schedules/exhibits, a
subset). Both arcs converge on the grid (clause questions = grid columns). This is a genuine
value-per-effort fork → put to the owner before emitting the Builder prompt.
