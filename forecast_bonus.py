"""
forecast_bonus.py — Forecast all GoalLab bonus questions for WC2026.

Bonus questions:
  1. Which team will score the first goal? (Deadline: Jun 11 11:00)
  2. Which team will score the most goals? (excl. penalty shootout) (Deadline: Jun 24)
  3. Which team will win the tournament? (Deadline: Jun 24)
  4. How many red cards in total? (yellow-red counts as red) (Deadline: Jul 4)
  5. How many games decided by penalty shootout? (Deadline: Jul 4)
  6. How many goals scored in total? (excl. penalty shootout) (Deadline: Jul 4)
  7. How many goals in the final match? (Deadline: Jul 4)

Usage:
    python forecast_bonus.py           # run all forecasts
    python forecast_bonus.py --dry-run # show questions only
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BASE_DIR, "results", "bonus")
os.makedirs(RESULTS_DIR, exist_ok=True)

BONUS_QUESTIONS = [
    {
        "id": "first_goal_team",
        "question": "Which team will score the first goal of the 2026 FIFA World Cup?",
        "deadline": "2026-06-11T11:00",
        "answer_type": "team_name",
        "context": "The first match is Mexico vs South Africa on June 11 at Estadio Azteca, Mexico City (Group A). "
                   "The second matches are South Korea vs Czech Republic and Canada vs Bosnia & Herzegovina on June 11-12. "
                   "Prediction: which team will score the tournament's first goal?",
    },
    {
        "id": "most_goals_team",
        "question": "Which team will score the most goals in the 2026 FIFA World Cup? (excluding penalty shootouts)",
        "deadline": "2026-06-24T11:00",
        "answer_type": "team_name",
        "context": "The group stage has 48 matches. Consider all 48 qualifying teams. Strong attacking teams: Brazil, France, Spain, Argentina, Germany, England, Portugal.",
    },
    {
        "id": "tournament_winner",
        "question": "Which team will win the 2026 FIFA World Cup?",
        "deadline": "2026-06-24T11:00",
        "answer_type": "team_name",
        "context": "2026 FIFA World Cup, 48 teams, hosted in USA/Canada/Mexico. Group stage + knockout rounds.",
    },
    {
        "id": "total_red_cards",
        "question": "How many red cards will be shown in total in the 2026 FIFA World Cup? (yellow-red counts as red)",
        "deadline": "2026-07-04T09:00",
        "answer_type": "integer",
        "context": "2026 WC has 104 matches total (48 group stage + 56 knockout). Historical average: ~0.25 red cards per match. 2022 WC had 14 reds. 2018 WC had 28 reds.",
    },
    {
        "id": "penalty_shootout_games",
        "question": "How many games in the 2026 FIFA World Cup will be decided by a penalty shootout?",
        "deadline": "2026-07-04T09:00",
        "answer_type": "integer",
        "context": "Only knockout games can go to shootout (56 knockout matches). Historical: 2022 WC had 3 shootouts, 2018 had 3, 2014 had 2. Usually 2-5 per tournament.",
    },
    {
        "id": "total_goals",
        "question": "How many goals will be scored in total in the 2026 FIFA World Cup? (excluding penalty shootouts)",
        "deadline": "2026-07-04T09:00",
        "answer_type": "integer",
        "context": "2026 WC has 104 matches (48 group + 56 knockout). 2022 WC: 172 goals in 64 matches (2.69/game). 2018: 169 in 64 (2.64/game). With 104 matches, expect proportionally more.",
    },
    {
        "id": "final_goals",
        "question": "How many goals will be scored in the 2026 FIFA World Cup final match? (excluding penalties)",
        "deadline": "2026-07-04T09:00",
        "answer_type": "integer",
        "context": "Recent WC finals: 2022 France 2-4 Argentina (6 goals, went to pens), 2018 France 4-2 Croatia (6 goals), 2014 Germany 1-0 Argentina (1 goal). Average ~3.0 goals.",
    },
]

PROOF_URL = "https://pages.github.tools.sap/I846720/WCFCST/"


def load_config():
    cfg_path = os.path.join(BASE_DIR, "config.json")
    with open(cfg_path, encoding="utf-8") as f:
        return json.load(f)


def _extract_json(text):
    import re
    text = text.strip()
    if text.startswith("{"):
        try:
            return json.loads(text)
        except Exception:
            pass
    m = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except Exception:
            pass
    return None


async def call_model_for_bonus(model, question_data, semaphore):
    import anthropic
    import httpx

    q = question_data
    prompt = f"""You are a sports analyst forecasting outcomes for the 2026 FIFA World Cup.

Question: {q['question']}

Context:
{q['context']}

Today is June 10, 2026. The tournament starts June 11, 2026.

Provide your best forecast answer. Also estimate prediction market probabilities if this is a selection question,
or provide a numeric estimate with confidence interval if this is a numeric question.

Respond ONLY with valid JSON:
{{
  "answer": "<your primary answer — team name or integer>",
  "confidence": <0-100 integer>,
  "reasoning": "<2-3 sentences>",
  "alternatives": "<2nd/3rd most likely answers if applicable>",
  "prediction_market_note": "<any relevant market data you know about>"
}}"""

    config = load_config()
    litellm_url = config.get("litellm_base_url", "http://localhost:6655/litellm/v1")

    async with semaphore:
        start = time.time()
        try:
            if model["sdk"] == "anthropic":
                client = anthropic.AsyncAnthropic()
                response = await client.messages.create(
                    model=model["id"],
                    max_tokens=400,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw = response.content[0].text
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens
            else:
                import openai as openai_lib
                hai_key = os.environ.get("HAI_API_KEY", os.environ.get("ANTHROPIC_API_KEY", ""))
                client_oai = openai_lib.AsyncOpenAI(api_key=hai_key, base_url=litellm_url)
                response = await client_oai.chat.completions.create(
                    model=model["id"],
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=400,
                )
                raw = response.choices[0].message.content
                input_tokens = getattr(response.usage, "prompt_tokens", 0)
                output_tokens = getattr(response.usage, "completion_tokens", 0)

            parsed = _extract_json(raw) or {}
            cost = (input_tokens / 1e6 * model["input_cost_per_million"] +
                    output_tokens / 1e6 * model["output_cost_per_million"])

            return {
                "question_id": q["id"],
                "model_short": model["short"],
                "model_id": model["id"],
                "vendor": model["vendor"],
                "answer": parsed.get("answer", ""),
                "confidence": int(parsed.get("confidence", 50)),
                "reasoning": parsed.get("reasoning", ""),
                "alternatives": parsed.get("alternatives", ""),
                "prediction_market_note": parsed.get("prediction_market_note", ""),
                "forecast_date": datetime.now().strftime("%Y-%m-%d"),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": round(cost, 6),
                "elapsed_sec": round(time.time() - start, 1),
                "error": None,
                "raw_response": raw,
            }

        except Exception as e:
            return {
                "question_id": q["id"],
                "model_short": model["short"],
                "model_id": model["id"],
                "vendor": model["vendor"],
                "answer": "",
                "confidence": 0,
                "reasoning": "",
                "alternatives": "",
                "prediction_market_note": "",
                "forecast_date": datetime.now().strftime("%Y-%m-%d"),
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
                "elapsed_sec": round(time.time() - start, 1),
                "error": str(e),
                "raw_response": "",
            }


def compute_consensus(results, question_data):
    """Compute consensus from all model results for one question."""
    valid = [r for r in results if not r.get("error") and r.get("answer")]
    if not valid:
        return None

    q = question_data
    answers = [r["answer"] for r in valid]

    if q["answer_type"] == "integer":
        # Median of numeric answers
        nums = []
        for a in answers:
            try:
                nums.append(int(str(a).strip().split()[0].replace(",", "")))
            except Exception:
                pass
        if nums:
            nums.sort()
            mid = len(nums) // 2
            consensus_answer = nums[mid] if len(nums) % 2 else (nums[mid-1] + nums[mid]) // 2
        else:
            consensus_answer = None
    else:
        # Plurality vote for team name
        from collections import Counter
        # Normalize team names
        normalized = []
        for a in answers:
            normalized.append(str(a).strip().title())
        counts = Counter(normalized)
        consensus_answer = counts.most_common(1)[0][0] if counts else None

    avg_confidence = sum(r.get("confidence", 50) for r in valid) / len(valid)

    return {
        "question_id": q["id"],
        "question": q["question"],
        "deadline": q["deadline"],
        "answer_type": q["answer_type"],
        "consensus_answer": str(consensus_answer) if consensus_answer is not None else "",
        "avg_confidence": round(avg_confidence, 1),
        "model_count": len(valid),
        "all_answers": answers,
        "forecast_date": datetime.now().strftime("%Y-%m-%d"),
        "total_cost_usd": round(sum(r.get("cost_usd", 0) for r in results), 6),
    }


async def forecast_all_bonus():
    config = load_config()
    models = config["models"]
    vendor_limits = config["settings"]["vendor_concurrency"]

    semaphores = {
        v: asyncio.Semaphore(n) for v, n in vendor_limits.items()
    }

    all_consensus = []

    for q in BONUS_QUESTIONS:
        print(f"\n=== {q['id']} ===")
        print(f"  {q['question']}")

        # Check if already computed
        consensus_path = os.path.join(RESULTS_DIR, f"{q['id']}_CONSENSUS.json")
        if os.path.exists(consensus_path):
            with open(consensus_path, encoding="utf-8") as f:
                existing = json.load(f)
            print(f"  Already exists: {existing['consensus_answer']} (confidence {existing['avg_confidence']})")
            all_consensus.append(existing)
            continue

        tasks = []
        for model in models:
            sem = semaphores.get(model["vendor"], asyncio.Semaphore(1))
            tasks.append(call_model_for_bonus(model, q, sem))

        results = await asyncio.gather(*tasks)

        # Save individual results
        for r in results:
            if r.get("answer"):
                fpath = os.path.join(RESULTS_DIR, f"{q['id']}_{r['model_short']}.json")
                with open(fpath, "w", encoding="utf-8") as f:
                    json.dump(r, f, indent=2, ensure_ascii=False)
                print(f"  [{r['model_short']}] {r['answer']} (conf={r['confidence']}) - {r.get('error') or 'ok'}")

        # Compute consensus
        consensus = compute_consensus(results, q)
        if consensus:
            with open(consensus_path, "w", encoding="utf-8") as f:
                json.dump(consensus, f, indent=2, ensure_ascii=False)
            print(f"  CONSENSUS: {consensus['consensus_answer']} (avg_conf={consensus['avg_confidence']}, n={consensus['model_count']})")
            all_consensus.append(consensus)

        await asyncio.sleep(1)

    return all_consensus


def generate_bonus_html(all_consensus):
    """Generate an HTML section for the bonus questions report."""
    lines = [
        '<!DOCTYPE html>',
        '<html lang="en">',
        '<head>',
        '<meta charset="UTF-8">',
        '<title>WC2026 Bonus Questions — LLM Forecasts</title>',
        '<style>',
        '* { box-sizing: border-box; margin: 0; padding: 0; }',
        'body { background: #0d1117; color: #e6edf3; font-family: -apple-system, "Segoe UI", monospace; font-size: 13px; line-height: 1.5; }',
        'h1 { font-size: 1.6em; color: #58a6ff; padding: 24px 32px 8px; }',
        'h2 { font-size: 1.1em; color: #79c0ff; padding: 20px 32px 8px; border-top: 1px solid #21262d; margin-top: 16px; }',
        '.meta { padding: 4px 32px 16px; color: #8b949e; font-size: 0.85em; }',
        '.card { background: #161b22; border: 1px solid #21262d; border-radius: 8px; margin: 8px 32px; padding: 16px 20px; }',
        '.question { font-size: 1.05em; color: #e6edf3; font-weight: 600; margin-bottom: 8px; }',
        '.answer { font-size: 1.8em; font-weight: 700; color: #3fb950; margin: 8px 0; }',
        '.deadline { color: #d29922; font-size: 0.85em; margin-bottom: 4px; }',
        '.conf { color: #8b949e; font-size: 0.85em; }',
        '.alternatives { color: #8b949e; font-size: 0.85em; margin-top: 6px; }',
        '.votes { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }',
        '.vote { background: #21262d; border-radius: 4px; padding: 2px 8px; font-size: 0.78em; color: #8b949e; }',
        '.vote-winner { background: #1a4d2e; color: #3fb950; font-weight: 600; }',
        '.proof { color: #58a6ff; font-size: 0.8em; margin-top: 8px; }',
        '</style>',
        '</head>',
        '<body>',
        '<h1>2026 FIFA World Cup — Bonus Question Forecasts</h1>',
        f'<p class="meta">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")} · {len(all_consensus)} questions · 12 models · Proof: <a href="{PROOF_URL}" style="color:#58a6ff">{PROOF_URL}</a></p>',
        '<h2>Consensus Forecasts</h2>',
    ]

    for c in all_consensus:
        # Count votes
        from collections import Counter
        vote_counts = Counter(str(a).strip().title() for a in c.get("all_answers", []))
        deadline_str = c.get("deadline", "").replace("T", " ")

        lines.append('<div class="card">')
        lines.append(f'<div class="deadline">Deadline: {deadline_str}</div>')
        lines.append(f'<div class="question">{c["question"]}</div>')
        lines.append(f'<div class="answer">{c["consensus_answer"]}</div>')
        lines.append(f'<div class="conf">Avg confidence: {c["avg_confidence"]}% · {c["model_count"]} models · Cost: ${c["total_cost_usd"]:.4f}</div>')

        if vote_counts:
            lines.append('<div class="votes">')
            for ans, cnt in vote_counts.most_common():
                cls = "vote vote-winner" if str(ans) == str(c["consensus_answer"]).title() else "vote"
                lines.append(f'<span class="{cls}">{ans} ({cnt})</span>')
            lines.append('</div>')

        lines.append(f'<div class="proof">Proof: <a href="{PROOF_URL}" style="color:#58a6ff">{PROOF_URL}</a></div>')
        lines.append('</div>')

    lines += ['</body>', '</html>']
    return "\n".join(lines)


def main():
    if "--dry-run" in sys.argv:
        for q in BONUS_QUESTIONS:
            print(f"[{q['deadline']}] {q['question']}")
        return

    all_consensus = asyncio.run(forecast_all_bonus())

    # Generate HTML report
    html = generate_bonus_html(all_consensus)
    html_path = os.path.join(BASE_DIR, "report", "bonus.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\nBonus HTML report saved: {html_path}")

    # Print summary
    print("\n=== FINAL CONSENSUS ===")
    for c in all_consensus:
        print(f"  [{c['question_id']}] {c['consensus_answer']} (conf={c['avg_confidence']})")


if __name__ == "__main__":
    main()
