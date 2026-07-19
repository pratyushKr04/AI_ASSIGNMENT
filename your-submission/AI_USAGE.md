# AI Usage Log

This document records all uses of AI tools throughout this assignment.

## Tool: Gemini / Claude (via Antigravity IDE agent)

### Session 1 — 2026-07-18
- **Used for:** Exploring the starter kit, identifying bugs in `fertility.py`, planning the approach, writing boilerplate scripts for corpus download and analysis, drafting initial memos, and performing KV cache calculations.
- **What I verified manually:** Bug hypotheses were confirmed by running `audit_evidence.py`. KV cache math was cross-checked against `model_spec.md`. Goodput was calculated from raw values in `bench_log.csv`.
- **What I wrote myself:** Final conclusions, recommendation language, and the decision memo reasoning.

### Session 2 — 2026-07-19
- **Used for:** Rewriting `build_corpus.py` to support interactive HuggingFace authentication (`HF_TOKEN`). Re-running all experiments on the official FLORES-200 devtest corpus (1012 sentences). Adding the lowercasing impact experiment. Revising audit conclusions to remove unsupported claims (e.g., removed the assertion that `tok/byte` is definitively the "fairest" metric). Rewrote Part C decision memo to correct constraint math (30 reviewer hours total, not per language), cover all 6 required languages, change the recommendation from prompt engineering to LoRA-based SFT, and strengthen success/kill criteria with measurable thresholds.
- **What I verified manually:** All updated numerical results were produced by actually running `audit_evidence.py` and `corrected_fertility.py` on the downloaded FLORES corpus. No numbers were invented or carried forward from prior runs without re-verification.
- **What I wrote myself:** All final engineering arguments, trade-off analyses, and conclusions in the memos. The AI provided code scaffolding and structural suggestions; all reasoning in the final text reflects my own understanding of the constraints.
