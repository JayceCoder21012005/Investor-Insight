# 12 — Evaluation

## Goal
Produce real, reproducible numbers for the report and README.

## Files
`scripts/run_eval.py`, `eval/results.md`, `eval/results.json`

## Command
`uv run python scripts/run_eval.py --runs 3 [--skip-llm]` — runs core and AI directly (no HTTP, no DB).

## Measurements
1. Detection — for each of the 33 persona files: compute flags; compare with `labels.json`. `overconfidence` is not declared by any persona: it is expected on files labeled `overtrading` whose `performance.excess < 0` (its definition in spec 05).
   - per flag id: TP, FP, FN, precision, recall
   - confusion table persona × flag
   - `insufficient_data` evaluated like a flag
2. AI — for each persona file, generate `--runs` reports:
   - first-attempt pass rate (no violations)
   - final pass rate (no template fallback)
   - count of `number_not_found` and `advice` violations
   - latency p50 / max
3. Speed — validate + metrics time p50 / max over 33 files, plus one synthetic 5,000-row file.

## Output
- `results.json`: all numbers + `formula_version`, `LLM_MODEL`, run date, git commit.
- `results.md`: three tables in Vietnamese, ready to paste into the report.
- When thresholds are tuned, keep the previous run under a "Trước hiệu chỉnh" heading.

## User test (manual, not scripted)
5 users try the demo or their own data, then rate 1–5: dễ hiểu, liên quan, hữu ích; plus one open question. Record averages in `results.md` by hand.

## Acceptance
- `--skip-llm` runs in under 60 s.
- Numbers in `results.md` match `results.json`.
