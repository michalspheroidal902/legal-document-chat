# BUILDER_STATE.md — Builder handoff (pre-context-clear)

_Regenerated 2026-06-21 at the **M-ENRICH-backlog boundary** (HEAD `40f02e7`). Snapshot of the Builder
tab's state in the Planner→Builder→Reviewer→Tester relay. Read alongside **`RELAY.md`** (loop manual) and
the canonical files it lists: `CLAUDE.md`, `RUN_STATE.md` (source of truth + "Next task" + **Audit
canon**), `TASKS_M2.md` (→ M-ENRICH), `DECISIONS.md` (**D-1…D-55**), `eval/TEST_PLAN.md` (§6 page+span bar).
The Builder is **IDLE at a clean between-task boundary — nothing in-flight, tree clean.**_

## 1. Current task

**NONE in progress — idle at a clean boundary.** The **M-ENRICH comprehensive backlog is COMPLETE**
(D-55), independently Tester-confirmed **240/240** and committed (`38d12ae` feat, `40f02e7` gov). Delivered
in one PROGRESS.md grind: **T-GRID** (review grid: `POST /grid` SSE doc×question matrix, bounded
concurrency ≤4, reuses `clauses._classify` — not forked); **B1–B6** small wins (`answering._norm` align,
`openapi_url=None`, compose-only README, logprob confidence display-only, **non-gating** fuzzy fallback,
streaming-chat SSE); **C1/C2** read-only retrieval experiments; **D1** PyMuPDF form-robustness (no new
dep). Never-false-accept held across grid/streaming/fuzzy; eval baselines byte-identical; 0 non-loopback.

_Prior beats (all DONE + committed): **T-TBL** Docling TableFormer tables (D-53, `5a325fc`); **T-CLAUSE**
Contract Review clause checklist (D-52, `37fa31d`); the SAM-style UI, M2/M3 gap-closure, M2-9, M2-8a all
earlier. Milestone is now the **M-ENRICH capability workstream** (post-M2-3)._

## 2. Decisions made (and why) — recent (full list in `DECISIONS.md` D-1…D-55)

- **D-49/D-51 — OSS-evaluation roadmap** (9 repos deep-dived + an independent Tester cross-eval): adopt
  Docling tables, the review grid, clause extraction, small wins; **our mechanical span verifier is the
  moat — never replace it with anyone's soft/fuzzy attribution.** Skip cloud/GraphRAG/server stores.
- **D-50/D-53 — Tables:** Docling TableFormer; **one Markdown table per chunk with SELF-RELATIVE offsets**
  (`[TABLE]` tag); **offset-routing — NEVER mix PyMuPDF and Docling offsets on one chunk**; prose keeps the
  PyMuPDF path byte-identical; `has_tables` gates the heavy Docling pass. `TABLEFORMER_REVISION` pinned +
  now code-enforced (fail-loud on mismatch).
- **D-52 — Clause checklist:** `extract_clauses(matter, doc_id?)` → 3-status (found = span-verified only /
  potentially_missing / not_confirmed); reuse, don't fork, the verifier.
- **D-54 — Builder protocol:** comprehensive PROGRESS.md grind, no stubs, "going slow OK," BUT a **`[GATE]`
  HARD-STOP** for new install/dep/model-fetch, real data, hardware, non-loopback bind, weakening the
  verifier, or re-indexing/re-running the eval baseline. Keep grinding all other tasks.
- **D-55 — F-026 fix PROVEN but GATED:** C1 measured top-k×N(20)+rerank recovers F-026 (None→rank3), but
  it's baseline-affecting → **owner decision to adopt**, NOT self-applied (`rerank=False` stays, D-36).
  **Audit canon re-pinned** to CWD-stable hashes via `scripts/baseline_hash.sh`.
- **Standing (unchanged): D-34** LanceDB embedded · **D-35** matter pre-filter-before-similarity · **D-36**
  reranker OFF by default · **D-37** hand-rolled answering (no LlamaIndex) · **D-38** chunk-derived
  citations · **D-39** page+span bar · **D-31** egress-monitored air-gap · **D-28** bodies/stores git-ignored.

## 3. In-flight work

**NONE.** No task is mid-edit; working tree is **clean** (verified). Everything from T-CLAUSE/T-TBL/
M-ENRICH is committed. `PROGRESS.md` (the backlog checklist) is committed as a historical record. The
two `[GATE]`/deferred items are recorded, not started: `eyecite` (new pip dep, owner-gated) and the
F-026-adopt decision (baseline-affecting, owner-gated).

## 4. Next 3 steps (immediately after resume)

1. **Do NOT auto-start anything.** The next task — **T-TRANS (transcripts: page:line citation + Q/A-aware
   chunking)** — is **BRAINSTORM-FIRST**: page:line reshapes the verifier + UI, so the Planner runs a
   design brainstorm with the owner BEFORE writing the Builder prompt. Await that comprehensive prompt.
2. When the Planner emits the T-TRANS prompt (or an owner-greenlit decision: **adopt F-026 fix** /
   **approve `eyecite`** / **OcrMac/MPS**), execute it test-first per the D-54 protocol.
3. On any new install/dep/model-fetch/baseline-reindex → **`[GATE]` HARD-STOP**, surface to the Planner.

## 5. Key constraints (must be respected — see `RELAY.md` "Standing constraints")

- **Local-only, loopback-only.** System Ollama `127.0.0.1:11434`; never bind `0.0.0.0`; never set
  `OLLAMA_HOST`. **Synthetic/public docs only — no real attorney/client data** (real = M6, written approval).
- **`[GATE]` HARD-STOP (D-54):** no new install/dep/model-fetch, real data, hardware, non-loopback bind,
  verifier-weakening, or baseline re-index/M2-8 re-run without surfacing to the Planner first.
- **Verifier fails CONSERVATIVELY — never false-accept a fabrication** (D-19/D-38). The fuzzy fallback
  (B5) is **non-gating**: "probable/unverified" UI only, NEVER enters the verified set.
- **Baselines byte-identical:** verify with the canonical **`scripts/baseline_hash.sh`** (CWD-independent).
  Pinned: `.lancedb=537146cf…`, `.lancedb_full=d329c91e…`, `.lancedb_hyb=07f04972…` (supersedes the old
  path-sensitive `13b242de…` set). Experiments run on scratch/KB stores only.
- **Egress = PID-scoped** (`lsof -a -p PID -iTCP`), 0 non-loopback, real samples in the audit-canon log
  format. A system-wide sample is not pipeline proof.
- **Installs owner-gated.** **No net-new installs this cycle.** Current venv deps (pinned): `pymupdf
  ==1.27.2.3`, `docling==2.104.0`, `lancedb==0.33.0`, `fastapi==0.118.0`, `uvicorn==0.34.3`, `httpx
  ==0.28.1`, `pytesseract==0.3.13`, `python-docx==1.2.0` (+ transformers/Torch from docling/reranker).
  **NOT installed (gated/avoided):** `eyecite` (`[GATE]`), `pdfplumber` (D1 reimplemented on PyMuPDF).
- **D-11 pins (a change forces re-index/re-eval):** `qwen3:14b=bdbd181c33f2`, `bge-m3=790764642607`,
  reranker `RERANKER_REVISION=953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e` (OFF by default, D-36),
  `TABLEFORMER_REVISION=fc0f2d45e2218ea24bce5045f58a389aed16dc23` (code-enforced). HF models live in
  `~/.cache/huggingface`, fetched once then OFFLINE (table_extract sets HF/Transformers offline at import).
- **Manual eval grading only** (no auto-scorer, TEST_PLAN §3/§5). **Git-ignored (D-28):** `documents/`,
  `pipeline/.lancedb*`, `pipeline/.kb_catalog.db`, chunk data, `eval/results/`; never commit a body/secret.

## 6. File map

**Tracked governance/eval (committable):** `RELAY.md`, `CLAUDE.md`, `CE_PLAN.md`, `README.md`,
`RUN_STATE.md` (+ Audit canon), `TASKS_M2.md` (→ M-ENRICH), `DECISIONS.md` (D-1…D-55), `PLANNER_STATE.md`,
`BUILDER_STATE.md` (this file), `PROGRESS.md` (last backlog run), `eval/TEST_PLAN.md`,
`eval/golden_manifest.jsonl` (72), `eval/golden_questions.jsonl`, `docs/research/2026-06-21-oss-evaluation.md`,
`docs/experiments/2026-06-21-retrieval-experiments.md`, `deploy/` (compose + README), `scripts/baseline_hash.sh`.

**Pipeline code (`pipeline/`, committable — code/tests only, no bodies):**
- Core RAG: `ingestion.py` · `chunking.py` · `embed_store.py` · `retrieval.py` · `reranker.py` (OFF) ·
  `answering.py` · `verifier.py` · `catalog.py` · `extractors.py` · `ingest_pipeline.py` · `kb_ingest.py`.
- M-ENRICH: `clauses.py` + `routes_clauses.py` + `data/clause_taxonomy.json` (T-CLAUSE) · `table_extract.py`
  + `table_ingest.py` + `build_table_corpus.py` (T-TBL) · `grid.py` + `routes_grid.py` (T-GRID) ·
  `fuzzy_fallback.py` (B5) · `kb_maintenance.py` (A0b prune) · `pdf_forms.py` + `build_form_corpus.py` (D1).
- API/UI: `api.py` (mounts routes; `openapi_url=None`) · `routes_chat.py` (+ streaming) · `routes_kb.py` ·
  `routes_matters.py` · `routes_settings.py` · `pdf_view.py` · `static/{app.html,app.css,app.js}` (SAM-style
  UI incl. the grid page + Contract Review panel).
- Experiments (committable): `experiments/exp_c1_topk_rerank.py`, `experiments/exp_c2_sentence_window.py`.
- Harnesses: `run_m28.py`, `run_m28a_rerun.py`, `run_hybrid_eval.py`, `run_latency.py`, `make_scans.py`,
  `build_scanned_corpus.py`, `build_full_store.py`. `tests/test_*.py` (per stage; TDD; 240 total).

**Git-ignored artifacts (NEVER committed, D-28):** `pipeline/.venv/`, `pipeline/.lancedb/` (eval baseline)
+ `.lancedb_full/` + `.lancedb_hyb/` + `.lancedb_kb/` (KB scratch) + `.kb_catalog.db`,
`documents/` (bodies + scanned + kb), `eval/results/` (raw runs + egress logs + grades).

## 7. Blockers / flags (to escalate to Reviewer / Tester / owner)

- **🟢 No reds.** 240/240; never-false-accept intact; baselines byte-identical; 0 non-loopback.
- **🟡 G-LAT `<3s` first-token latency (~3.6s)** — the one open §2/M3 quantitative yellow; hardware-
  hypothesis (D-22), unproven. NOT a defect. (Builder cannot resolve — hardware/model lever, held out.)
- **🟡 F-026 fix PROVEN but un-adopted** (C1) — turning on top-k×N+rerank is baseline-affecting → **owner
  decision**, not a Builder default. `eyecite` install is `[GATE]` (owner approval).
- **Owner-gated, OUT of Builder scope:** T-TRANS is brainstorm-first; M4 UAT/`/app` screenshot; M4-5
  hardware; M6 real data. Do not start these from the Builder tab.
