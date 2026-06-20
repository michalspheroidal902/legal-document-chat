# PLANNER_STATE.md — Planner handoff (pre-context-clear)

> Snapshot of the Planner tab's state. Read alongside `RELAY.md` (loop manual), `RUN_STATE.md` (source
> of truth + Next task), `DECISIONS.md` (D-1..D-39), `TASKS_M2.md`, `eval/TEST_PLAN.md`. Most Planner
> state already lives in those files; this captures only the forward-looking judgment that doesn't.

## Role
Scope + sequencing owner. Read `RUN_STATE.md` "Next task" → write the next **Builder prompt**
(small, test-first, owner-gated, self-contained, ends by instructing the Builder to emit the Reviewer
prompt). Surface genuine forks to the **owner** via a question; never change a locked decision alone.
Record every decision into `DECISIONS.md`; keep `RUN_STATE.md` + `TASKS_M2.md` current. Flag each new
install at its gate.

## Current position
**M2-8 = CONDITIONAL PASS** (page+span capability proven). **Next task = M2-8a** (verifier
normalization fix: `html.unescape` + strip backslash-escaped quotes + F-042 alternate-page → targeted
re-run → FINAL PASS ≥95%). The M2-8a Builder prompt has been written (see the last Planner turn /
re-derive from `RUN_STATE.md` Next task + `TASKS_M2.md` M2-8a + `TEST_PLAN.md` §6).

## Remaining M2-3 sequence (after M2-8a)
- **M2-7** — FastAPI loopback HTTP surface (D-13; LlamaIndex was dropped, D-37, but FastAPI stands).
  Last build step; loopback-only, no `0.0.0.0`.
- **M2 milestone wrap** — record the milestone result (custom pipeline cleared the page+span bar the
  turnkey stack failed). Then the project looks toward **M4-5 hardware** (owner decision, no purchase
  on spec — D-21/D-22) and eventually **M6** (onsite real data, written approval).

## Anticipated forks to put to the owner (don't pre-decide)
- **M2-7:** API auth/shape for a loopback single-user service (likely none/minimal — confirm).
- **Pre-M4 demo:** latency tuning pass (qwen3 "thinking" mean ~19s/Q vs <3s target) — when + how.
- **Before M6 (real data):** the open **real-PDF section-heading robustness** risk (Docling
  `section_header` detection vs the synthetic `#` markers) must be validated on heading-less PDFs.

## Watch items / carry-forward (also in RUN_STATE/TASKS_M2)
- Verifier must **fail conservatively** (D-38/M2-6) — never weaken fabrication rejection to chase %.
- Reranker stays **OFF by default** (D-36, neutral lift) until real-scale justifies it.
- Egress-monitored air-gap (D-31) on every full run; manual scoring only (no auto-scorer).

## How I resume
Read `RUN_STATE.md` "Next task". If a Tester report is pending, process it (record results +
decisions, update docs), then emit the next Builder prompt. If a fork blocks the next task, ask the
owner first.
