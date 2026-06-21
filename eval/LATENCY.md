# First-token latency (TTFT) — measured (Task 6 / G-LAT)

_Reading-aid measurement, 2026-06-20. Harness: `pipeline/run_latency.py`._

## Method
- 63 present-fact golden questions, the SAME grounded prompt `answer()` builds.
- TTFT = wall-clock from request-send to the first non-empty content token of the
  streamed qwen3:14b response. Knobs applied: **no-think** (`think=False`) + **warm
  `keep_alive=10m`** (no cold reload between questions).
- `answer()` body is unchanged (M2-7 parity); this is a streaming side channel.
- Loopback Ollama only; egress-monitored (`eval/results/egress-2026-06-20-t6.log`): 0
  non-loopback. Raw per-question data: git-ignored `eval/results/latency-2026-06-20.jsonl`.

## Result (honest — target NOT met)

| metric | TTFT |
|--------|------|
| mean   | 2.77s |
| median | 3.09s |
| p95    | 4.35s |

**CE_PLAN <3s first-token target: NOT met** (median 3.09s, just over). Many questions
do come in under 3s (TTFT floor ~1.8s), but the median sits just above the line.

## Honest conclusion
With no-think + a warm model, TTFT is dominated by **prompt prefill of the 5-chunk
grounded context on the 14B model** — not by reasoning. The remaining gap to <3s is a
hardware/model-size problem, not a prompt bug. Legitimate pre-M4 levers (not done here,
flagged): a smaller/quantized first-token model, GPU/production hardware (M4-5, no
purchase on spec), or trimming retrieved context (fewer/shorter chunks). Recorded as an
honest datapoint, not a silent miss; the instrumentation now exists to re-measure after
any of those changes.
