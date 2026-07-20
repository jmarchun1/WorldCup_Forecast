---
title: "fix: v4 forecast accuracy improvements"
type: fix
status: active
created: 2026-06-20
depth: standard
---

# fix: v4 Forecast Accuracy Improvements

## Problem Frame

After 29 scored matches, the LLM consensus is running at 1.28 P/G but the competition leader is at ~1.7 P/G. Four concrete bugs and missed-signal issues have been identified:

1. **GPT-5 parse errors** — ~15/29 games have no forecast from gpt5 due to multi-line `reasoning` values and lack of `response_format: json_object` on the OpenAI-compatible path.
2. **Null-goals scoring bug** — `_call_model()` silently coerces `null` goals to `0` via `or 0`, so contaminated Sonar forecasts (which return `null` goals) are scored as 0-0 predictions and occasionally awarded exact-score points.
3. **No explicit scoreline instruction** — the prompt ends without a clear "write your answer as home_goals-away_goals" instruction, contributing to varied output formats.
4. **Draw under-prediction** — the consensus is 0-for-10 on draws in 29 matches; the prompt nudges models toward confident wins when Elo gap is small. Historical WC draw rate is ~26% but models are predicting draws far less often.

**Scope:** `forecast.py`, `score.py`, `docs/_template.html`, `push_to_pages.py`. No schema changes. No new dependencies.

---

## Success Criteria

- GPT-5 scores in ≥25/29 played matches (currently ~14)
- Sonar/sonarpro exact scores only when `home_goals` is non-null in the forecast file
- Consensus P/G improves on the next 10+ matches relative to v3 baseline of 1.28
- Version History table in GitHub Pages shows v4 with release notes
- Dashboard deployed and accessible at `https://pages.github.tools.sap/I846720/WCFCST/`

---

## Scope Boundaries

### In scope
- Four code fixes in `forecast.py` and `score.py`
- Draw-probability prompt injection
- v4 release notes section in `docs/_template.html`
- Re-running `forecast.py --force` to generate v4 forecasts
- Scoring and deploying via `auto_score.py`

### Deferred to Follow-Up Work
- Brier-weighted consensus aggregation (high effort, needs more data)
- Per-model Elo lookup for dynamic draw-probability threshold
- Sonar pre-kickoff context fetching (currently blocked by leakage architecture)
- Removing the dead first accuracy IIFE in `_template.html` (cosmetic, no user-facing impact)

---

## Key Technical Decisions

| Decision | Choice | Rationale |
|---|---|---|
| GPT-5 fix approach | Add `response_format={"type":"json_object"}` to litellm OpenAI vendor calls | Cleanest fix; forces structured output without changing model behaviour for other vendors |
| Null-goals fix | Preserve `null` in parsed output; set `error="null_goals"`; null-check in scoring | Fixes both the coercion bug and the scoring pass-through in one change |
| Draw instruction | Inject after `"Probabilities must sum to 1.0."` in `build_prompt()` | Least invasive; doesn't change prompt structure |
| Explicit scoreline instruction | Add final line before JSON schema: `"Your predicted scoreline: {home_goals}-{away_goals}."` | Forces models to commit to a scoreline in the reasoning before the JSON output |
| Release notes location | `VERSION_HISTORY` extended with `notes` field; rendered in existing version history table | No new sections needed; existing push_to_pages.py injection path reused |

---

## Implementation Units

### U1. Fix null-goals coercion in `_call_model()`

**Goal:** Preserve `None` goal values instead of silently coercing to `0`; mark affected records with `error="null_goals"` so scoring skips them correctly.

**Files:**
- `forecast.py` — lines ~256–270 in `_call_model()`

**Approach:**
- Replace `int(parsed.get("home_goals") or 0)` with an explicit None-preserving cast
- When either goal is None after parsing, set `error="null_goals"` in the returned dict instead of `error=None`
- The existing `score_match()` null-check at `score.py:108` already skips records where `home_goals is None`, so no change needed there

**Test scenarios:**
- Model returns `{"home_goals": null, "away_goals": 1, ...}` → record has `home_goals=None`, `error="null_goals"`
- Model returns `{"home_goals": 0, "away_goals": 0, ...}` → record has `home_goals=0`, `away_goals=0`, `error=None` (0 is a valid score)
- Model returns fully valid JSON → unchanged behaviour, `error=None`

**Verification:** Run `python -c "import forecast; ..."` unit smoke test or inspect a sonar forecast JSON after re-run — should show `home_goals: null` not `home_goals: 0`.

---

### U2. Fix GPT-5 parse errors via `response_format`

**Goal:** Eliminate the ~50% parse-error rate on gpt5 by requesting structured JSON output from the OpenAI-compatible litellm endpoint.

**Files:**
- `forecast.py` — `_call_model()`, the `else` (litellm) branch ~lines 210–222

**Approach:**
- For models where `vendor == "openai"`, pass `response_format={"type": "json_object"}` in the `client.chat.completions.create()` call
- Guard with a try/except — if the model or litellm version doesn't support this parameter, fall back silently to the existing path
- Also add a **Repair 4** to `_extract_json()` for multi-line reasoning: use a `re.DOTALL` approach to strip/truncate the `reasoning` value before final parse, as a last-resort repair for models that don't support `response_format`

**Test scenarios:**
- GPT-5 with `response_format` set → model returns clean JSON, `_extract_json()` parses on first pass
- Non-OpenAI vendor (Anthropic, Gemini) → `response_format` not passed, behaviour unchanged
- Litellm endpoint that rejects `response_format` → exception caught, retries without it

**Verification:** After re-run, count `error` field across all `gpt5_*.json` files — expect <5 parse errors.

---

### U3. Inject draw-probability and explicit scoreline instructions into prompt

**Goal:** Reduce draw under-prediction and parse failures by (a) nudging models toward realistic draw probability when Elo gap is small and (b) requiring an explicit `X-Y` scoreline commitment in the reasoning.

**Files:**
- `forecast.py` — `build_prompt()`, `WC_BASE_RATE_PRIOR` constant, and `PREDICTION REQUEST` section

**Approach:**
Two injections in `build_prompt()`:

1. **Draw reminder** (after `"Probabilities must sum to 1.0."`):
   > "Draw base rate reminder: World Cup group-stage matches end in a draw ~26% of the time. When implied odds suggest an evenly-matched game (home-win and away-win probabilities both between 0.28 and 0.45), a draw (especially 1-1) is the single most likely outcome. Do not assign draw_prob below 0.15 unless one team is a clear favourite."

2. **Explicit scoreline instruction** (final line before the JSON schema):
   > "State your predicted scoreline in your reasoning as: 'Predicted score: X-Y'. Then output the JSON."

**Test scenarios:**
- Evenly-matched game (odds ~2.8/3.2/2.6) → `draw_prob` ≥ 0.18 in output
- Strong favourite (odds 1.4/4.5/7.0) → `draw_prob` may stay low, no floor violation
- Reasoning field contains `Predicted score: X-Y` pattern

**Verification:** After re-run, compute average `draw_prob` across all future-match forecasts — should be ≥ 0.18 vs v3 baseline (estimate ~0.12).

---

### U4. Add v4 release notes to VERSION_HISTORY and dashboard

**Goal:** Surface the four v4 improvements as human-readable release notes in the GitHub Pages accuracy tab, tied to the new archive version.

**Files:**
- `push_to_pages.py` — `_build_version_history()` function
- `docs/_template.html` — version history table render (accuracy tab IIFE, ~lines 855–867)

**Approach:**

**`push_to_pages.py`:**
- Add a `RELEASE_NOTES` dict mapping archive version stamp prefixes to release note strings
- Extend each version dict with a `notes` field: look up by version stamp prefix (e.g., `"20260620"`)
- Hard-code v4 notes: "v4: fix null-goals scoring bug, fix gpt5 parse errors (response_format), draw-probability prompt boost, explicit scoreline instruction"

**`_template.html`:**
- Extend the version history table with a `Notes` column
- Render `v.notes` in the new column (empty string if absent, so older versions render cleanly)

**Test scenarios:**
- Version with a notes entry → Notes column shows the release notes text
- Version without a notes entry → Notes column renders empty cell
- Build with no VERSION_HISTORY → accuracy tab shows "No archived versions yet" as before

**Verification:** `push_to_pages.py --no-push` builds successfully; inspect `index.html` for the Notes column in the version history table.

---

## Execution Sequence

```
U1 (null-goals fix) ──┐
U2 (gpt5 fix)        ├──→ run forecast.py --force (v4)
U3 (draw prompt)     ──┘        │
                                ↓
                        run auto_score.py (score + push)
                                │
U4 (release notes) ─────────→ push_to_pages.py (deploy)
```

U1–U3 must all land before running `forecast.py --force`. U4 can be applied independently but should deploy after the v4 forecast run so the version history table includes the new archive entry.

---

## Deferred Implementation Notes

- The exact Elo gap threshold for the draw reminder is not knowable until we see whether 0.28–0.45 odds bracket correctly identifies the 10 misclassified draws. Adjust in v5 if still under-predicting.
- `_extract_json()` Repair 4 (multi-line reasoning) may be redundant once `response_format` is working for gpt5. Implement defensively but don't over-engineer.
- Dead first accuracy IIFE in `_template.html` (lines 547–704) is deferred cleanup.
