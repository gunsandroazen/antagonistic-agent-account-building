---
name: account-scoring
description: Use after data/target-description.md exists and optionally after account-search has produced data/accounts-raw/. Two modes — Generate derives scoring/rules.py + scoring/rules.md + scoring/weights.yaml from the target description AND calibrates initial weights empirically against Closed-Won (not guessed); Run executes the algorithm against accounts-raw, normalizes schemas to Closed-Won shape, produces T1-T4 tiers with contribution-explained scores, and runs a mandatory sense-check that scores Closed-Won through the same pipeline. Emits audit artifacts rich enough that the user can answer "why is this account T1?" for any row. Never silently overwrites user-owned scoring files.
---

# Account Scoring Skill

## Your role

Generate a scoring algorithm from the target description that is empirically grounded in the user's own Closed-Won data, then run it against the raw account list and produce actionable tiers with a hard sense-check gate. You are not building a black-box — every scored account must be explainable.

Two modes:
- **Generate mode:** Read target-description.md, produce `scoring/{rules.py, rules.md, weights.yaml}`. Weights are calibrated, not guessed: run each rule against the Closed-Won CSV to measure precision (share of Closed-Won that matches) and use lift vs. population baseline to set the starting weight.
- **Run mode:** Execute the algorithm against `data/accounts-raw/deduped-*.csv`, emit tiers, run sense-check, write audit artifacts.

---

## Mode selection

- If `scoring/rules.py` does not exist → **Generate mode.**
- If `scoring/rules.py` exists AND `data/accounts-raw/deduped-*.csv` exists → **Run mode.**
- If both exist, default to Run mode. Warn: *"scoring/ already exists. Delete scoring/rules.py to regenerate, or explicitly ask to regenerate."* Never silently overwrite.
- If `scoring/rules.py` exists but no accounts-raw, print: *"scoring/ is in place. Run `/skill account-search` first to produce data/accounts-raw/, then re-invoke account-scoring for run mode."*

---

## Tooling

- Python + pandas + PyYAML. If PyYAML isn't available, read/write weights.yaml via a small hand-rolled parser (only handles the subset we use: scalars, dicts, lists, comments).
- For LLM rules in run mode, use Claude via the Claude SDK if `ANTHROPIC_API_KEY` is set; otherwise use whatever model CLI the user has (`codex`, `gemini`). If none configured, skip LLM rules and record that in the manifest.
- Never call external APIs from within `scoring/rules.py` — rules.py is pure deterministic Python. All model calls happen in run-mode orchestration outside the rule functions.

---

## Generate mode (detailed)

### Step 1 — Parse target-description.md

Extract the structured content. Distinguish:
- **Firmographic signature** bullets → positive-weight deterministic rules.
- **Disqualifiers** → large-negative-weight rules.
- **Confidence notes → Strong signal** → higher-weight rules.
- **Confidence notes → Soft signal** → lower-weight rules.
- **Known unknowns** → NOT turned into rules. Noted in rules.md as commented gaps for the user to consider.

### Step 2 — Draft `scoring/rules.py`

One function per bullet in firmographic signature + one per disqualifier. Each function takes a `row: dict` and returns `bool` (for categorical / threshold rules) or `float` in [0, 1] (for graded rules — e.g., "headcount closer to 150 scores higher than 50 or 300").

Every function:
- One-line docstring citing the source pattern (e.g., `"""Firmographic: Headcount 50-300 (lift 12.5x per target-description)."""`)
- Handles None / missing columns without crashing.
- Handles common type coercions (int-from-string for headcount, string-contains for tech stack).
- Uses standard column names from the Closed-Won CSV (read the header in step 4 to confirm — if the column isn't in Closed-Won, note it in a `# TODO` comment and use the best-guess name from accounts-raw).

Bundle rules into sections: `# --- Firmographic ---`, `# --- Tech stack ---`, `# --- Disqualifiers ---`, `# --- Graded (return float 0-1) ---`.

### Step 3 — Draft `scoring/rules.md`

For every LLM-rule candidate (concepts from the target description that can't be evaluated from structured data alone — buyer-persona classifications, positioning assessments, market-stage judgments), write a block with:
- Rule name
- When to invoke (which accounts need it — don't run LLM rules on every account; gate by cheap deterministic filters first)
- Research instructions (which URLs, what to look for, what evidence is sufficient)
- Return type and schema
- Cache key (usually `domain`)

Also add a commented section at the bottom listing every "Known unknown" from the target description — prompts for the user to think about whether an LLM rule could fill that gap.

### Step 4 — Calibrate initial weights empirically

**This is the step that makes generated weights actually usable.** Do not guess. Compute:

1. Read `data/closed-won/*.csv`.
2. For each rule in rules.py (EXCEPT disqualifiers), run it against every Closed-Won row.
3. Record `precision_on_closed_won` = fraction of Closed-Won rows where the rule returned True (for booleans) or >0.5 (for graded).
4. Look up the rule's dimension in `.claude/skills/antagonist/baselines/b2b-population-baselines.json`. If found, compute `lift` = `precision_on_closed_won / baseline`.
5. Set the starting weight:
   - `lift >= 10`: weight 30
   - `lift 5-10`: weight 20
   - `lift 2-5`: weight 15
   - `lift 1.5-2`: weight 10
   - `lift < 1.5`: weight 5, but also add a comment `# Low lift — consider removing` in weights.yaml
   - `baseline not found`: fall back to precision: `precision >= 0.80 → 20`, `>= 0.50 → 10`, `else → 5`.
6. Disqualifier rules get weight -1000.
7. LLM rules: start at 15 regardless. The user tunes after observing behavior.
8. Graded rules: the weight multiplies the returned float, so treat the weight as the "max score when rule is fully satisfied."

### Step 5 — Write `scoring/weights.yaml`

Include the calibration data as comments so the user sees *why* each weight was chosen:

```yaml
# TWEAK THIS. These weights are an empirical starting hypothesis, not gospel.
# Your judgment beats the LLM's.
#
# Calibration procedure: each rule was run against data/closed-won/*.csv to measure
# precision on Closed-Won. Lift was computed vs. the B2B population baseline where
# available. Starting weights follow the lift-to-weight table in
# .claude/skills/account-scoring/SKILL.md.
#
# Re-run with `delete scoring/rules.py; /skill account-scoring` to regenerate.

generated_at: "2026-04-23T14:32:01Z"
calibration_source: "data/closed-won/acme-closed-won-2026q1.csv"
closed_won_row_count: 847

rules:
  headcount_in_target_band:
    weight: 25                              # lift 12.5x, precision 94%
    type: boolean
    description: "Headcount 50-300"
    calibration:
      precision_on_closed_won: 0.94
      population_baseline: 0.075
      lift: 12.5

  hq_in_northeast:
    weight: 20                              # lift 3.2x, precision 71%
    type: boolean
    description: "HQ in US Northeast"
    calibration:
      precision_on_closed_won: 0.71
      population_baseline: 0.22
      lift: 3.23

  has_segment_in_stack:
    weight: 30                              # lift 85x, precision 85% (very high-signal)
    type: boolean
    description: "Segment in tech stack"
    calibration:
      precision_on_closed_won: 0.85
      population_baseline: 0.01
      lift: 85.0

  is_public:
    weight: -1000                           # disqualifier
    type: boolean
    description: "Disqualifier: public company"

  sells_to_data_teams:
    weight: 15                              # LLM rule — default starting weight
    type: llm
    description: "Sells primarily to data/analytics/eng buyers"

tiers:
  sense_check_threshold: 0.80
  t1:
    percentile_min: 0.99
    named_accounts_file: null
  t2:
    percentile_min: 0.90
  t3:
    percentile_min: 0.60
  t4:
    score_floor: 10

llm:
  preferred_model: "claude-sonnet-4-6"      # configurable
  cache_file: "data/accounts-scored/.llm-cache.json"
  run_on_tier_candidates_only: true          # only invoke LLM rules on accounts already scoring T3+ by deterministic rules (save cost)
```

### Step 6 — Output summary

Print:
```
Generate mode complete.
  Rules created:
    - Deterministic boolean: <N>
    - Deterministic graded: <M>
    - Disqualifier: <D>
    - LLM-assisted: <L>
  Calibrated against: <csv> (<N_rows> Closed-Won rows)
  Weights set empirically using lift-to-weight table.

Files:
  scoring/rules.py       — hand-edit to add/remove rules or tighten logic
  scoring/rules.md       — hand-edit LLM rule instructions
  scoring/weights.yaml   — tune weights to match your judgment

Next: `/skill account-scoring` (run mode) once account-search has produced data/accounts-raw/.
```

---

## Run mode (detailed)

### Step 1 — Load inputs

1. Load `scoring/weights.yaml` and dynamically `import` `scoring/rules.py` (use `importlib.util.spec_from_file_location`). Enumerate all functions; cross-reference against `weights.yaml`. Error if any rule in rules.py is missing from weights.yaml or vice versa.
2. Find the most recent `data/accounts-raw/deduped-*.csv`. Load with pandas.
3. Load `data/closed-won/*.csv` for the sense-check later.
4. Parse `data/accounts-raw/manifest.json` to understand how the dedup list was built.

### Step 2 — Schema harmonization

Compare the dedup list columns to the Closed-Won columns. For any column a rule uses:
- If present in both with same name, straightforward.
- If present with different names, apply a canonical mapping (see `account-search` Stage 5). Maintain a mapping dict and log it.
- If present in Closed-Won but absent in accounts-raw, the rule will return False by default for accounts-raw rows — flag this in the output manifest as `rules_that_cannot_fire_on_raw: [list]`.
- If present in accounts-raw but absent in Closed-Won, the sense-check won't be able to evaluate that rule — warn but continue.

### Step 3 — Apply deterministic rules

For each row in accounts-raw:
- Run every function in rules.py (EXCEPT LLM rules).
- Record a dict `rule_results: {rule_name: result}`.
- Compute `deterministic_score = sum(weight * result for rule, result in rule_results.items())` treating `True` as 1 and `False` as 0 for boolean rules, using the float value directly for graded rules.

### Step 4 — Apply LLM rules (gated)

If `weights.yaml → llm.run_on_tier_candidates_only == true`, identify the top 30% of accounts by deterministic_score. For those rows only, run LLM rules:
- For each LLM rule in rules.md, check cache (`data/accounts-scored/.llm-cache.json`, keyed by `<rule_name>|<domain>`). If hit, use cached result.
- If miss, invoke the model per the rule's instructions. Record result + cost + timestamp in cache.
- On model error, record `rule_result = null` and note the error in the account's `llm_errors` field; do not silently treat as False.

### Step 5 — Compute final score + tiers

For each row:
- `final_score = deterministic_score + sum(weight * result for llm_rule_name, result in llm_results.items() if result is not None)`
- If ANY disqualifier rule fires (result==True for a disqualifier), set `final_score = 0` regardless of other contributions.
- Compute top-3-contributing-rules (positive weights only, sorted by `weight * result` descending).

Assign tier:
1. If `named_accounts_file` is set and the row's domain is in that file → T1.
2. Else use percentiles:
   - `percentile_rank(final_score) >= tiers.t1.percentile_min` → T1
   - `>= tiers.t2.percentile_min` → T2
   - `>= tiers.t3.percentile_min` → T3
   - `final_score >= tiers.t4.score_floor` → T4
   - Else → `excluded`

### Step 6 — Write outputs

`data/accounts-scored/tiered.csv` columns:
- All original columns from deduped-raw
- `score` (final_score)
- `tier` (T1 | T2 | T3 | T4 | excluded)
- `top_rules` (comma-joined `rule_name:contribution`; e.g., `"has_segment_in_stack:30,headcount_in_target_band:25,hq_in_northeast:20"`)
- `disqualifier_fired` (null or rule_name)
- `llm_rules_evaluated` (count)
- `llm_errors` (null or comma-joined list)

Also write `data/accounts-scored/run-manifest.json`:

```json
{
  "generated_at": "2026-04-23T14:32:01Z",
  "accounts_scored": 47891,
  "tier_distribution": { "T1": 479, "T2": 4310, "T3": 14367, "T4": 23945, "excluded": 4790 },
  "rules_that_cannot_fire_on_raw": [],
  "llm_rules_run": ["sells_to_data_teams", "modern_brand_positioning"],
  "llm_cache_hits": 12847,
  "llm_cache_misses": 1573,
  "llm_cost_estimate_usd": 4.71,
  "schema_mapping_applied": { "organization_num_employees": "headcount", "hq_location": "hq_city" },
  "sense_check": { "...see Step 7..." }
}
```

### Step 7 — Sense-check gate (REQUIRED)

Run the exact same pipeline against `data/closed-won/*.csv`:
- Score each Closed-Won row through the same deterministic + LLM pipeline.
- Compute tier for each (using the SAME percentile thresholds as accounts-raw — do NOT re-rank Closed-Won standalone; rank them within the combined distribution so T1 means the same thing).
- Compute `closed_won_t1_t2_share` = fraction of Closed-Won in T1 or T2.

Read `weights.yaml → tiers.sense_check_threshold` (default 0.80).

**If closed_won_t1_t2_share < threshold:**

Emit a prominent warning:
```
⚠️  SENSE-CHECK FAILED
Only <X.X>% of your Closed-Won landed in T1/T2 (threshold: <Y>%).
Your algorithm does not recognize your own best customers.

Root causes to investigate:
  1. Misclassified Closed-Won: <N> rows landed in T3/T4/excluded.
     See data/accounts-scored/closed-won-sense-check.csv — sort by tier ascending.
     For each misclassified row, check which rules failed.
  2. Rules that fire on <10% of Closed-Won may be over-fit to outliers — check:
     <list of such rules with their firing rates>
  3. Disqualifier rules that incorrectly fired on Closed-Won:
     <list with counts>

Remediation checklist:
  [ ] Review data/accounts-scored/closed-won-sense-check.csv bottom rows
  [ ] Lower weight or delete rules with <20% Closed-Won firing rate
  [ ] Check disqualifier logic for false positives
  [ ] Re-run /skill account-scoring after edits
```

Write `data/accounts-scored/closed-won-sense-check.csv` with every Closed-Won row + its score + tier + top_rules + per-rule-firing. This IS the audit trail.

**If closed_won_t1_t2_share >= threshold:**
Print `"Sense-check passed: <X.X>% of Closed-Won in T1/T2 (threshold: <Y>%)."`

Do NOT skip the sense-check for any reason. If the Closed-Won file is missing, STOP with an error — don't silently proceed.

### Step 8 — "Explain this account" helper

Generate `data/accounts-scored/explain.md` with a template for digging into specific accounts:

```markdown
# Explain a scored account

To understand why any account got its tier, look up its row in `tiered.csv` and inspect:
- `top_rules` — the 3 biggest positive contributions to its score.
- `disqualifier_fired` — if non-null, explains a T0/excluded verdict.
- `llm_errors` — if non-null, note that LLM rules failed to evaluate.

To see which Closed-Won accounts are similar, grep the `closed-won-sense-check.csv`
for rows with the same top_rules pattern.

For a deeper dive on any account, ask Claude Code:
  "Explain tier for <domain>. Load scoring/rules.py and scoring/weights.yaml,
   load the row from tiered.csv, and walk through each rule's result and weight."
```

---

## Anti-patterns

- Do NOT silently rewrite `scoring/weights.yaml` on re-runs. User owns that file.
- Do NOT skip the sense-check.
- Do NOT produce a single-tier output.
- Do NOT call external APIs inside `scoring/rules.py` — deterministic rules are pure Python.
- Do NOT pretend LLM rules succeeded when they failed — surface `llm_errors`.
- Do NOT re-rank Closed-Won in isolation during the sense-check. Closed-Won rows are scored within the combined distribution so "T1" means the same thing on both sides.
- Do NOT generate rules for patterns listed under "Known unknowns" — those are flags for the user, not rules.

---

## When done (run mode)

Print:

```
Scoring complete.
  Scored: <total> accounts
  Tier distribution:
    T1:       <A>   (<A%>)   # hand-picked + top 1% by score
    T2:       <B>   (<B%>)   # top 10% — SDR outbound focus
    T3:       <C>   (<C%>)   # top 40% — ads / programmatic
    T4:       <D>   (<D%>)   # above floor — nurture / watchlist
    Excluded: <E>   (<E%>)   # disqualifier fired or below floor
  LLM rules: <N_rules> run on top <30%>, cache hits <hits>/<total>
  Estimated LLM cost: $<X.XX>

Sense-check: <PASSED / FAILED>
  <X.X%> of Closed-Won landed in T1/T2 (threshold <Y>%)

Outputs:
  data/accounts-scored/tiered.csv
  data/accounts-scored/closed-won-sense-check.csv
  data/accounts-scored/run-manifest.json
  data/accounts-scored/explain.md

Next steps:
  - If sense-check FAILED: open closed-won-sense-check.csv, find misclassified rows, tweak scoring/weights.yaml, re-run.
  - If sense-check PASSED: T1 is your ABM list. T2 is your SDR focus. T3 is for paid/programmatic. Go to market.
```
