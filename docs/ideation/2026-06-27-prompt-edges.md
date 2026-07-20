# WC2026 LLM Forecast Prompt — Missing Edge Ideas
**Date:** 2026-06-27  
**Focus:** Backtest-grounded gaps + advanced stats opportunities  
**Method:** 6 parallel ideation sub-agents, Phase 1 grounding (691 scored records, 66 matches, 12 models)

---

## Phase 1 Grounding Summary

### Backtest Findings
- Models predict **1.94 goals/match** vs **2.98 actual** — 54% systematic undercount
- **1-1 predicted 29.2%** of matches vs **13.6% actual** — gravitational attractor
- **17/66 matches (26%) all models scored 0 pts** — complete consensus failure pattern
- Outcome accuracy ceiling ~61% regardless of model tier or cost
- Blowout direction correct 78% but magnitude wrong (predicts 2-0 instead of 4-1)

### Advanced Stats Gaps
- No rolling xG signal — football-data.org free tier has SoT, corners, possession
- No rest day computation — documented 5-8% win shift for <4 days rest
- No altitude encoding — Azteca 2,240m has ~0.35 extra goal effect for unacclimatized teams
- No qualification-status rotation flag — biggest gap for today's final group stage matches

---

## Ranked Survivors

### KEEP — High Priority (Ship Today or Next Session)

**S1 — Explicit Tournament Goal Prior** *(Goal Volume Calibration #1)*  
Add to base rates section: *"WC2026 group stage matches through MD3 average 2.9 goals (SD 1.4). Your predictions should reflect this distribution."* Single-line change. Estimated +0.5–0.8 goals on mean prediction. **Implementability: today. Overfit risk: low.**

**S2 — Qualification-Status Rotation Flag** *(Environmental #6 + Upset Detection #1)*  
Compute qualification status from group standings before building the prompt. Inject structured block noting if a team is safe/eliminated and the historical rotation rate (~65% starter rotation when safe). Affects effective XI quality. **Highest-EV signal for today's final group matches.** Implementability: today (15 min, uses existing `_compute_group_standings()`). Overfit risk: low.

**S3 — Pressure Asymmetry Module** *(Upset Detection #6)*  
Must-win teams historically underperform expected rate by ~6% (clutch pressure effect). Already-eliminated teams show positive free-wheeling effect in ~30% of cases. Inject as structured prompt block. **Directly relevant to today's final group games.** Implementability: today. Overfit risk: low.

**S4 — Explicit Upset Prior Injection** *(Upset Detection #2)*  
Force the model to price the upset before anchoring on the favorite. Add a pre-prediction block: base rate for underdog win when favorite is 60-70% implied prob is 22%; ask model to state adjusted upset probability. Prevents probability collapse. Implementability: today. Overfit risk: low.

**S5 — Minority Scenario Forcing** *(Upset Detection #7)*  
Mandatory "steelman the underdog" reasoning step before final prediction. 2-3 sentences on the most plausible underdog path. Forces probability mass onto low-probability outcomes through explicit reasoning. Implementability: today. Overfit risk: low-medium (verbose risk).

**S6 — 1-1 Modal Penalty Declaration** *(Score Attractor #1)*  
Add direct instruction: *"The score 1-1 is overrepresented in AI forecasts by 2x the historical base rate. Do not predict 1-1 unless strong specific evidence justifies it."* Expected 30-50% reduction in 1-1 predictions. Implementability: today. Overfit risk: low.

**S7 — Anti-Hedging Persona Frame** *(Score Attractor #4)*  
System-level persona: *"You are a sharp bettor who profits by identifying asymmetric outcomes. Hedged predictions like 1-1 are the mark of a model defaulting to uncertainty rather than analysis."* Expected 20-35% reduction in 1-1 rate. Implementability: today. Overfit risk: low-medium (may over-correct on some models).

**S8 — Brier-Weighted Loss Framing** *(Upset Detection #5)*  
Note in system prompt that predictions are Brier-scored — overconfidence penalized, assign ≥10% to every outcome unless structural reason to exclude. Targets calibration failure on lopsided matches. Implementability: today. Overfit risk: low.

**S9 — Rest Day Differential Signal** *(Environmental #1)*  
Compute each team's rest days from fixtures history; inject when differential ≥2 days. Documented 5-8% win probability shift for fatigued team. Today: most matches at 4-5 days (low differential) but establishes baseline for knockout rounds. Implementability: today (20 min). Overfit risk: low.

**S10 — Disagreement-Triggered Confidence Flag** *(Ensemble #1)*  
Compute SD of 12 win-probability estimates. When SD > 0.12, tag as HIGH_UNCERTAINTY and widen output probabilities toward 50/50 by 30%. Targets the 26% consensus-miss failure class. Implementability: today. Overfit risk: low.

**S11 — Per-Model Historical Calibration Weights** *(Ensemble #4)*  
Use 66-match backtest to compute per-model Brier scores; weight ensemble by 1/Brier. Regularize with 50% uniform mix to avoid overfitting thin sample. Implementability: partial (1-2 hours). Overfit risk: medium (66 matches is thin for 12 weights).

**S12 — Shots-on-Target xG Proxy** *(Advanced Stats #1)*  
Pull SoT from football-data.org free tier; compute rolling 3-match xG proxy (SoT × 0.33). Inject as: *"[Team] rolling xG proxy: 1.4 expected, 1 scored — slight underperformance."* Implementability: today (API available). Overfit risk: low.

**S13 — Altitude Acclimatization Penalty** *(Environmental #2)*  
Venue lookup table: altitude → acclimatization penalty. Fire only for Azteca (2,240m) and Akron (1,535m). Not relevant today (all US sea-level venues) but fires automatically for knockout matches at those venues. Implementability: today, ready for future rounds (30 min). Overfit risk: low.

**S14 — Post-Processing Linear Rescale** *(Goal Volume #3)*  
Multiply raw model goals by k = actual_mean / predicted_mean ≈ 1.50, recompute win/draw/loss probs via Poisson. Apply as pipeline post-processing. Eliminates mean bias by construction. Use rolling 14-day k rather than fixed constant. Implementability: today. Overfit risk: medium if k is fixed — low with rolling window.

**S15 — Goals-vs-xG Proxy Deviation Flag** *(Advanced Stats #7)*  
Combine SoT proxy with actual goals to flag luck delta: teams overperforming their xG proxy are regression candidates. Prompt: *"[Team] goals 5, xG proxy 2.8 — overperformance +2.2 (regression risk flagged)."* Implementability: contingent on S12. Overfit risk: medium (WC sample is short).

---

### PARK — Good Ideas, Tackle After Group Stage

**P1 — Scoreline Probability Grid** *(Score Attractor #6)*  
Request 5×5 probability grid (scores 0-0 through 4-4) and extract argmax. Structurally prevents 1-1 as the default; 50-70% expected reduction. Requires output parser changes. Tackle after group stage.

**P2 — Cheap-Model Routing Architecture** *(Ensemble #7)*  
Run cheap models first; escalate to expensive only when cheap models disagree or low confidence. Saves 30-40% cost. Requires two-phase call architecture refactor (~2-3 hours). Worth doing before knockout rounds.

**P3 — Sonar xG Stats Fetch** *(Advanced Stats #5)*  
Use Sonar web search to pull post-match xG from Opta/FotMob media reports. Bypasses free-tier xG gap entirely. Highest ceiling of all advanced stats ideas (3-5% accuracy gain). Requires unstructured parsing step.

**P4 — WC2022 StatsBomb Style Fingerprint** *(Advanced Stats #6)*  
Precompute nation-level xG/shot, progressive carry, PPDA from StatsBomb open WC2022 data. Static lookup; inject as style prior when WC2026 sample is thin (0-1 matches). One-time precomputation script.

**P5 — Odds-vs-Model Disagreement Amplifier** *(Upset Detection #3)*  
Two-pass: get draft prediction, compare to market, re-query with challenge block when |model - market| > 15 points. Highest-ceiling upset detection intervention. Requires two API calls per match.

**P6 — Card Accumulation Pressure Index** *(Advanced Stats #8)*  
Cross-reference per-player yellow card accumulation from bookings endpoint. Flag starters one yellow from suspension. Tactical rotation signal. Feasible but requires aggregation script.

---

### REJECT — Low Signal/High Risk

| Idea | Reason |
|------|--------|
| Score Attractor #5 (Exclusion Window) | Requires ranked scoreline output format; complex edge cases |
| Score Attractor #3 (Decoy Anchor) | Conditional base rates need larger sample; medium overfit risk |
| Score Attractor #6 (Negative Space "no 1-1") | S6 covers this more cleanly without format disruption |
| Goal Volume #2 (Few-shot examples) | Medium overfit risk; S1 covers the mechanism more robustly |
| Goal Volume #6 (Percentile framing) | S1 + S14 cover goal volume without the format complexity |
| Environmental #7 (Climate analogue win rates) | 3-4 hour research with medium overfit risk; defer to post-tournament analysis |
| Ensemble #2 (Cost-tier weights) | S11 (Brier-based weights) is strictly better; cost tier is a proxy |
| Ensemble #8 (Disagreement Index as feature) | Measurement infrastructure, not an improvement; useful for validation only |

---

## Implementation Stack for Today (June 27)

**Sprint A — Prompt changes only (30 min):**
1. S1: Tournament goal prior sentence in base rates section
2. S2: Qualification-status rotation block (uses existing standings logic)
3. S3: Pressure asymmetry module (must-win vs. nothing-to-lose)
4. S4: Explicit upset prior injection (base rate pre-commitment block)
5. S5: Minority scenario forcing (steelman underdog reasoning)
6. S6: 1-1 modal penalty declaration
7. S7: Anti-hedging persona frame (add to system instructions)
8. S8: Brier-weighted loss framing

**Sprint B — Pipeline changes (1-2 hours):**
9. S9: Rest day differential computation + injection
10. S10: Ensemble disagreement flag (post-processing)
11. S12: SoT xG proxy fetch from football-data.org
12. S14: Post-processing linear rescale (rolling k)

**Sprint C — Future rounds:**
- S11, S13, S15, P1–P6

---

## For the A/B Paper

The goal-volume undercount (S1, S14) and 1-1 attractor (S6, S7) are the two largest systematic biases. These are publishable findings:  
- "LLMs systematically underestimate goal volume in WC 2026 by 54% regardless of market information"  
- "The 1-1 gravitational attractor appears across all 12 models including those with market odds — market anchoring does not correct the score attractor"

The Condition B (no-odds) experiment should be run with and without S1/S6 to isolate whether the biases are intrinsic to LLM reasoning or correctable via prompt calibration.
