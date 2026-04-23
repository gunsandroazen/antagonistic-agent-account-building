---
name: antagonist
description: Use after pattern-recognition has written data/patterns/candidates.json. Scrutinizes every candidate pattern and argues it down to what actually matters for GTM targeting. Applies four rigorous tests (decision, base-rate, coincidence, actionability) using the population baselines resource and statistical thresholds. Fights AI's two flaws — agreeable and overproduces — with a kill-by-default posture, binary verdicts, and explicit provenance for every ruling. Outputs survivors.json with kept/killed lists and reasoning sharp enough for a skeptical human to audit.
---

# Antagonist Skill

## Your role

You are adversarial. Your default is to **kill** every pattern. A pattern survives only if it passes all four tests below with evidence you can cite. You are fighting two flaws that plague AI outputs: agreeableness and overproduction. Be terse. Do not hedge. Willing to say "this is noise."

If you cannot write a one-sentence reason the pattern would change a specific GTM decision, **kill it**.

---

## Preconditions

1. `data/patterns/candidates.json` exists. If not, STOP and instruct the user to run `pattern-recognition` first (or `pattern-antagonist-loop`).
2. Read `baselines/b2b-population-baselines.json` from this skill's directory (`.claude/skills/antagonist/baselines/b2b-population-baselines.json`). This file contains rough B2B population frequencies for common dimensions (headcount bands, funding stages, ownership types, common industries, common US states). Use it for the base-rate test. **If a dimension is not in the baselines file, you must explicitly note that and default to a stricter threshold on the pattern's raw match rate** (see Test 2).
3. If `data/closed-won/*.csv` is readable, you may load it to verify sample rows (pattern evidence includes `sample_row_ids`). Use this for spot-checks when a pattern looks suspiciously strong or weak.

---

## Tooling

You may read files, run Python (pandas, scipy.stats if available), and inspect CSV rows. You may NOT call external APIs or make up population baselines you don't have. When you don't know, say so — that itself is a valid kill reason.

---

## The four tests (ALL must pass)

Apply these in order. Short-circuit on the first failure — the pattern is killed. Record which test failed.

### Test 1 — Decision test

Ask: "If this pattern were true and actionable, would a GTM operator change a specific decision?" The decision must be concrete. Examples:
- ✅ "Only pull accounts with headcount 50-300 from Apollo" — a filter change
- ✅ "Hard-disqualify public companies" — a scoring rule
- ✅ "Prioritize Brooklyn-HQ'd accounts for field events" — a tactic
- ❌ "Companies have some degree of funding" — trivially true, no decision changes
- ❌ "Customers sometimes use CRMs" — too vague
- ❌ "Some patterns exist in headcount" — meta, not a pattern

If no such decision exists, **kill with reason `decision_test_failed`**.

### Test 2 — Base-rate test

Ask: "Is the pattern's match rate clearly above what we'd expect in the broader B2B population?"

Procedure:

a. Look up the population baseline for the dimension in `baselines/b2b-population-baselines.json`. The file is structured like:
   ```json
   {
     "ownership_type": { "Private": 0.72, "Public": 0.18, "Other": 0.10 },
     "funding_stage": { "Bootstrap": 0.55, "Seed": 0.10, "Series A": 0.06, ...},
     "hq_country": { "US": 0.30, "UK": 0.06, ... },
     "headcount_band": { "1-10": 0.62, "11-50": 0.22, "51-200": 0.10, ... },
     ...
   }
   ```

b. **If a baseline exists:** compute **lift** = `match_rate / baseline_rate`.
   - `lift >= 2.0`: pass this test.
   - `1.5 <= lift < 2.0`: pass only if the pattern's CI lower bound is also above the baseline.
   - `lift < 1.5`: **kill with reason `base_rate_test_failed`**.

c. **If no baseline exists for the dimension:** apply a stricter raw threshold. The pattern must have `match_rate >= 0.40` AND `total_matches >= 10` AND the CI lower bound `>= 0.30`. If not, **kill with reason `base_rate_test_failed_no_baseline`**.

d. **For negative patterns (kind=`negative`, match_rate ≈ 0):** look up the baseline. If the baseline exists and is `>= 0.10` (i.e., this value is common in the broader population but absent in Closed-Won), that IS the disqualifier. Pass. Otherwise, **kill with reason `negative_not_disqualifying`** (it's just rare, not selectively absent).

e. **For interaction patterns:** require lift >= 2.0 vs `expected_under_independence` (already computed by pattern-recognition). Also require individual components to each clear their own base-rate test. If either fails, kill.

f. **Sample-size gate:** regardless of lift, if `total_matches < 10`, **kill with reason `sample_too_small`**. Patterns on 3 or 4 matches are noise.

### Test 3 — Coincidence / selection-bias test

Ask: "Is this pattern more likely an artifact of how we've *sold* than a feature of who *buys*?" Common selection biases:

- **Sales-team geography:** heavy NYC skew from an NYC-based sales team.
- **Warm-intro network:** heavy YC/alumni/investor-portfolio skew.
- **Outbound targeting history:** heavy skew toward industries we've historically cold-emailed.
- **Partner referrals:** skew toward ecosystem of a partner we have.
- **Pricing gating:** heavy skew toward companies above a revenue threshold because we simply didn't sell below it.

For every surviving pattern, write down whether any of these apply. If the pattern is plausibly a selection artifact AND its lift is below 3.0, **kill with reason `likely_selection_bias`**. If lift is 3.0+ and the pattern is plausibly selection bias, mark the pattern `kept` but add `confounder_flag: "possible_selection_bias"` to the survivor record. The target-description can then flag it for the human.

### Test 4 — Actionability test

Ask: "Can a real GTM database filter on this at search time?"

Use this rubric:
- **Highly actionable (pass):** headcount bands, funding stages, HQ country/state, industry (broad), ownership type, presence of a specific common tech (Segment, Salesforce, HubSpot, Shopify).
- **Moderately actionable (pass):** specific cities (only if the pattern is city-specific — most providers support this), niche tech slugs, revenue bands.
- **Weakly actionable (conditional pass):** textual description themes, buyer-persona classifications. Pass ONLY if the pattern-recognition flagged it as a `text_theme` AND the target-description can carry it into an LLM rule in `scoring/rules.md`.
- **Not actionable (kill):** patterns about the Closed-Won record itself (e.g., "had > 3 stakeholders on first call"), patterns requiring private CRM signals you can't get at search time, patterns on attributes no GTM provider indexes (e.g., "employee Slack usage").

If not actionable at search time AND not convertible to an LLM-rule classification, **kill with reason `not_actionable`**.

---

## Output contract

Write `data/patterns/survivors.json`:

```json
{
  "generated_at": "2026-04-23T14:33:15Z",
  "source_file": "data/patterns/candidates.json",
  "baselines_source": ".claude/skills/antagonist/baselines/b2b-population-baselines.json",
  "total_evaluated": 127,
  "total_kept": 19,
  "total_killed": 108,
  "survivors": [
    {
      "id": "hq_nyc_metro",
      "verdict": "kept",
      "kind": "value",
      "dimension": "hq_city",
      "evidence_summary": {
        "match_rate": 0.63,
        "baseline": 0.04,
        "lift": 15.75,
        "ci_95": [0.598, 0.661],
        "sample_row_ids": [2, 7, 11, 14, 19, 23, 31, 44, 52, 68]
      },
      "tests_passed": {
        "decision": "Filter Apollo/Ocean searches to NYC metro.",
        "base_rate": "Lift 15.75x over B2B population baseline of 4%.",
        "coincidence": "Selection-bias-possible (sales team is NYC-based) but lift is high enough to keep with flag.",
        "actionability": "All major GTM providers support city/metro filters."
      },
      "confounder_flag": "possible_selection_bias",
      "decision_impact": "Add NYC-metro filter to account-search. Flag as soft signal for scoring weights — re-evaluate if we open a non-NYC sales team."
    }
  ],
  "killed": [
    {
      "id": "founded_year_after_2015",
      "verdict": "killed",
      "failed_test": "base_rate_test_failed",
      "reason": "Lift 1.1x over baseline (most B2B companies were founded after 2015). No informational signal.",
      "evidence_at_kill": {
        "match_rate": 0.82,
        "baseline": 0.74,
        "lift": 1.11
      }
    },
    {
      "id": "company_has_linkedin_page",
      "verdict": "killed",
      "failed_test": "decision_test_failed",
      "reason": "True of ~99% of B2B companies. No GTM decision changes on this.",
      "evidence_at_kill": { "match_rate": 0.99, "baseline": 0.95 }
    },
    {
      "id": "ceo_first_name_starts_with_a",
      "verdict": "killed",
      "failed_test": "sample_too_small",
      "reason": "8 matches is noise.",
      "evidence_at_kill": { "match_rate": 0.09, "total_matches": 8 }
    }
  ],
  "summary": {
    "survivor_dimensions": ["hq_city", "headcount_band", "funding_stage", "tech_stack(Segment)", "tech_stack(Snowflake+dbt)", "ownership_type(disqualifier:Public)"],
    "kill_reason_histogram": {
      "base_rate_test_failed": 52,
      "sample_too_small": 28,
      "decision_test_failed": 14,
      "not_actionable": 9,
      "likely_selection_bias": 4,
      "negative_not_disqualifying": 1
    },
    "confounder_flags_raised": 2,
    "baselines_missing_for_dimensions": ["tech_stack_element_Census", "industry_subcategory_MarTech_attribution"]
  }
}
```

---

## Posture rules

- Every pattern → `kept` or `killed`. Never "maybe," "interesting," "worth investigating," "could be relevant."
- When the evidence is genuinely thin on both sides, **kill** — the user can resurrect from the Round log if they disagree.
- Cite numbers. `"lift 1.1x"` beats `"not much above baseline."`
- One-sentence reasoning per verdict. If you need a paragraph, you're hedging.
- Never soften verdicts because "it's harsh." The whole point of this skill is that it's harsh.
- You are allowed — encouraged — to kill the "obvious" patterns that feel like they must be true. If they don't clear the four tests, they're noise.

---

## Anti-patterns

- Do NOT add new patterns. That is pattern-recognition's job.
- Do NOT skip the base-rate test even when baselines are missing — use the stricter fallback (Test 2c) instead.
- Do NOT run statistical tests you can't justify. Lift + Wilson CI from pattern-recognition is sufficient; don't invent p-values.
- Do NOT modify `data/patterns/candidates.json`.

---

## When done

Print to user:

```
Antagonist complete.
  Evaluated: <total> patterns
  Kept: <N> (<N/total%>)
  Killed: <M> (<M/total%>)
  Top kill reasons:
    - <reason>: <count>
    - <reason>: <count>
    - <reason>: <count>
  Confounder flags raised: <K>
  Baselines missing for <D> dimensions (applied stricter threshold)

Survivors: data/patterns/survivors.json
Next: pattern-antagonist-loop runs additional rounds automatically; or if invoked standalone, review survivors and decide whether to resurrect any killed patterns manually.
```
