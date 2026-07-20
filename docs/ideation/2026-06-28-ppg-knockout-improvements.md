---
name: ppg-knockout-improvements
description: PPG improvement ideas for WC2026 knockout round — 48 candidates across 6 frames, synthesized to 12 survivors
metadata:
  type: project
  date: 2026-06-28
  baseline_ppg: 1.054
  contest_v2_ppg: 1.102
  target_ppg: 1.2-1.4
---

# PPG Improvement Ideation — Knockout Round
**Date**: 2026-06-28 | **Stage**: R32+ begins today

## Context

Aggregate PPG after group stage: **1.054** (contest v2: **1.102**). Top human forecasters: **1.2–1.4**.
Remaining gap: ~0.1–0.3 PPG. 48 ideas generated across 6 frames. 12 survivors after adversarial filtering.

## Key Structural Failures (Group Stage)

| Failure | Impact |
|---------|--------|
| Goal undercount: 2.3 predicted vs 2.98 actual | Shifts scorelines down by ~0.7 goals/match |
| Draw detection: 27.9% hit rate on actual draws | ~7 missed draws × ~3pts gap = 21 lost pts |
| 1-1 attractor: 22.7% of predictions (was) | Fixed to ~7.8% in contest v2 |
| Home/prestige bias: +15-20pp home advantage | Systematic overconfidence on strong home teams |

---

## Tier 1 — Implement Immediately

### 1. Goal Count Rescaling Multiplier (F4-1)
**Mechanism**: Post-processing step multiplies all predicted goal totals by ~1.30 before final scoreline selection. 2.3 predicted × 1.30 ≈ 2.99 actual.
**Implementation**: 30 min — single constant in `_compute_consensus()` before mode selection.
**Backtest cost**: Zero (replay existing 72-match outputs).
**Expected PPG**: +0.05–0.10.
**Status**: ⬜ TODO

### 2. Poisson Scoreline Generator (F2-5 / F3-1 / F5-1 merged)
**Mechanism**: LLM outputs win/draw/loss probabilities only. Poisson model (Dixon-Coles calibrated on WC2026) generates the scoreline from those probabilities. Eliminates the 1-1 attractor entirely — it's a language model artifact, not a Poisson artifact.
**Implementation**: 2-3h — scipy Poisson, lambda estimation from Elo+odds, hook into `_compute_consensus()`.
**Backtest cost**: Zero (reuses existing win-prob outputs).
**Expected PPG**: +0.08–0.15 (highest ceiling of any single idea).
**Status**: ⬜ TODO

### 3. Scoreline EV Commit Rule (F4-2 / F6-4)
**Mechanism**: For each candidate scoreline S, compute `EV(S) = P(exact)×4 + P(same_GD)×2 + P(same_result)×1`. Pick max-EV scoreline, not max-frequency. A 25% chance at 2-1 beats a 30% chance at 1-0 because EV(2-1)=4×0.25+2×0.25+1×0.45=2.0 > EV(1-0)=4×0.30+2×0.30+1×0.40=2.2... margin cases exist.
**Implementation**: 1-2h — rewrite `_compute_consensus()` scoreline selection.
**Backtest cost**: Zero.
**Expected PPG**: +0.03–0.07.
**Status**: ⬜ TODO

### 4. Superforecaster Draw Floor (F5-4)
**Mechanism**: Mechanical rule: if Kalshi implied draw > 0.27 AND ensemble draw_prob < 0.20, override draw_prob to max(ensemble_dp, 0.27). Prevents the v2 draw-suppression from over-correcting.
**Implementation**: 30 min — add 3 lines to `_compute_consensus()`.
**Backtest cost**: Zero.
**Expected PPG**: +0.04–0.08.
**Status**: ⬜ TODO

### 5. Knockout-Specific Prompt Persona (F6-1)
**Mechanism**: Add explicit elimination-stakes block to the knockout prompt: "Both teams motivated to win outright. Favourites push forward harder. Historic R32 slight underdog (35-45% implied) wins outright ~30% — higher than group stage." No draw suppression (draws are valid ~20% of the time in KO). Replace 1-1 attractor warning with forward-pressure framing.
**Implementation**: 30 min — extend `build_contest_prompt()` for knockout stage.
**Backtest cost**: ~$8 (re-run KO matches when corpus grows).
**Expected PPG**: Uncertain until R32 ground truth, but structurally sound.
**Status**: ✅ URGENT — Netherlands-Morocco and Mexico-Ecuador currently predict 1-1

---

## Tier 2 — This Week

### 6. Kalshi Market-Override for Draws (F5-7)
If Kalshi implied draw > ensemble draw_prob by >0.10, override scoreline to a draw. Mechanical complement to the verbal draw gate.
**Status**: ⬜ TODO

### 7. Dissent-Weighted Ensemble (F2-2)
When 10/12 models agree and 2 are outliers, the outliers might be right. Promote dissenter picks in high-disagreement matches for 4-pt exact-score captures.
**Status**: ⬜ TODO

### 8. Post-Match Rolling Re-Forecast + Ensemble Reweighting (F5-6 / F6-8)
Re-run models on next-round matches after each day resolves. Inject updated tournament-so-far context. Pair with per-round PPG reweighting so recently-calibrated models carry more weight.
**Status**: ⬜ TODO

### 9. Cross-Model Consensus Gate (F4-5)
When 7+/12 models agree on exact scoreline, commit directly. When <4 agree, run EV pass on top-3 scorelines only.
**Status**: ⬜ TODO

### 10. No-Sonar Variant (F2-7)
Test whether Sonar's narrative context amplifies prestige bias. $8 backtest run.
**Status**: ⬜ TODO

---

## Tier 3 — Interesting But Risky

### 11. Bookmaker Odds as Adversary (F3-2)
Predict blind, compare to market. Only override when model vs market diverges >15pp. Complex decision rule, risk of adding noise.

### 12. Minority-Outcome Specialization (F3-3)
Force 1-2 models to argue for the upset/draw before consensus. Pilot on 10 matches needed before full backtest.

---

## Rejected Ideas (key reasons)

- **F3-4 Referee stats**: Data unavailable for WC2026 at match level
- **F3-5 Single best model**: Consensus at 1.29 already beats best individual (sonnet 1.21)
- **F4-6 Prompt temperature per match**: Not exposed in LiteLLM proxy
- **F2-4 / F4-8 Auto model retirement**: Weights range 0.078–0.087 (too flat to matter)
- **F5-2 Kalman filter**: 4+ hours, needs inter-match-day state management
- **F6-6 Penalty encoding**: GoalLab scores 90-min result only

---

## Priority Implementation Order (Today)

1. ✅ Fix knockout no-draw constraint → re-run Netherlands-Morocco, Mexico-Ecuador
2. Implement goal rescaling multiplier (30 min, zero API cost)
3. Implement draw floor override (30 min, zero API cost)
4. Implement EV commit rule (1-2h, zero API cost)
5. Backtest all three on 72-match scored corpus
6. Poisson scoreline generator (2-3h, highest ceiling)
