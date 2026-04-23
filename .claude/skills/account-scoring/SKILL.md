---
name: account-scoring
description: Use after data/target-description.md exists and the user wants to generate or run a scoring algorithm that turns the description into tiers (T1/T2/T3/T4). Two modes — (1) generate scoring/rules.py + scoring/rules.md + scoring/weights.yaml from the target description, or (2) run the existing scoring/ against data/accounts-raw/ and write data/accounts-scored/tiered.csv. Human is expected to hand-tweak weights and hard-code rules after generation.
---

# Account Scoring Skill

## Your role

Two modes:
- **Generate mode:** Turn `data/target-description.md` into a concrete scoring algorithm under `scoring/`.
- **Run mode:** Execute the algorithm against the raw account list to produce tiers, then sense-check against the user's own Closed-Won.

You are NOT expected to produce a perfect algorithm on the first pass. The human will hand-edit `scoring/weights.yaml` and probably `scoring/rules.py`. Design for iteration.

## Mode selection

- If `scoring/rules.py` does not exist → **Generate mode.**
- If `scoring/rules.py` exists AND `data/accounts-raw/` contains at least one `.csv` → **Run mode.**
- If both exist and the user has not explicitly asked to regenerate → **Run mode**, with a warning: *"scoring/ already exists. If you want to regenerate from a new target description, delete scoring/rules.py first or explicitly ask to regenerate."*
- **Never silently overwrite `scoring/*`.** Regeneration is always explicit.

---

## Generate mode

Read `data/target-description.md`. Produce three files:

### `scoring/rules.py`

Pure Python. Each rule is a function that takes a single row (dict with column name → value) and returns either a numeric score or a boolean. One function per pattern from the target description. Every function has a one-line docstring stating which pattern it implements.

Example shape:

```python
"""Deterministic scoring rules. Generated from data/target-description.md.
Hand-edit freely — this file is yours."""

def headcount_in_target_band(row: dict) -> bool:
    """Firmographic signature: Headcount 50-500."""
    try:
        hc = int(row.get("headcount", 0))
    except (TypeError, ValueError):
        return False
    return 50 <= hc <= 500

def hq_in_target_region(row: dict) -> bool:
    """Firmographic signature: HQ in US Northeast."""
    return row.get("hq_state", "").upper() in {"NY", "MA", "CT", "NJ", "PA", "RI", "VT", "NH", "ME"}

# Disqualifier
def is_public_company(row: dict) -> bool:
    """Disqualifier: public companies — our Closed-Won is 100% private."""
    return row.get("ownership_type", "").lower() == "public"
```

### `scoring/rules.md`

LLM-rules: narrative description of the rules that require classification, web research, or judgment that deterministic code can't do. The run-mode engine uses this to know when to call out to a model.

Shape:

```markdown
# LLM-assisted scoring rules

## rule: sells_to_smb
Use when we need to classify whether a company sells primarily to SMBs (<500 employees) vs. enterprise. Deterministic data rarely captures this directly. Research the company's website and case studies if available. Return boolean.

## rule: has_ai_positioning
Does the company position itself as AI-native or AI-forward in current marketing? Research homepage + recent blog posts.
```

### `scoring/weights.yaml`

YAML with one entry per rule (both py and md), plus threshold config. Header comment must include: `# TWEAK THIS. These weights are a starting hypothesis, not gospel. Your judgment beats the LLM's.`

Shape:

```yaml
# TWEAK THIS. These weights are a starting hypothesis, not gospel.
# Your judgment beats the LLM's.
#
# Total possible score = sum of all positive weights when all rules return True.
# Disqualifier rules (negative weights or boolean-gated) can zero out a score entirely.

rules:
  headcount_in_target_band:
    weight: 25
    type: boolean
    description: "Firmographic: headcount 50-500"

  hq_in_target_region:
    weight: 20
    type: boolean
    description: "Firmographic: US Northeast"

  is_public_company:
    weight: -1000   # effective disqualifier
    type: boolean
    description: "Disqualifier: public company"

  sells_to_smb:
    weight: 15
    type: llm
    description: "Classification: sells to SMB"

# Tier thresholds (percentile-based unless hand-picked list is provided)
tiers:
  sense_check_threshold: 0.80   # at least 80% of Closed-Won must land in T1 or T2
  t1:
    percentile_min: 0.99         # top 1%
    named_accounts_file: null    # optional path to hand-picked list (csv with domain column)
  t2:
    percentile_min: 0.90         # top 10% (excluding T1)
  t3:
    percentile_min: 0.60         # top 40% (excluding T1/T2)
  t4:
    score_floor: 10              # minimum score to make T4 at all (else excluded from output)
```

Print after generating: `"scoring/ generated. Hand-edit weights.yaml and rules.py to match your judgment, then re-run this skill to score."`

---

## Run mode

1. **Normalize columns.** Read `data/accounts-raw/deduped-*.csv` (or the most recent file matching that pattern). Compare its columns to `data/closed-won/*.csv`. Map columns so that the rules in `scoring/rules.py` can run against raw-account rows. If there's no clean mapping for a column a rule needs, surface the gap to the user and stop.

2. **Apply deterministic rules.** For each row, run every function in `scoring/rules.py`.

3. **Apply LLM rules.** For each rule in `scoring/rules.md`, call out to Claude (or whichever model the user has configured) as described in the rule body. Cache results by domain in `data/accounts-scored/.llm-cache.json` to avoid re-billing on re-runs.

4. **Compute weighted score.** For each row, sum `weight * rule_result` across all rules. Disqualifier rules with large negative weights zero out the score effectively.

5. **Assign tiers** per `weights.yaml` thresholds. Named accounts (if a file is provided) always become T1.

6. **Write `data/accounts-scored/tiered.csv`** with columns:
   - All original columns from the raw list
   - `score` (numeric)
   - `tier` (T1 | T2 | T3 | T4 | excluded)
   - `top_rules` (comma-joined: top 3 contributing rules + their weighted contributions)

7. **Sense-check gate — REQUIRED, DO NOT SKIP.**
   - Run the same scoring pipeline against `data/closed-won/*.csv`.
   - Compute share of Closed-Won rows landing in T1 or T2.
   - Read threshold from `weights.yaml → tiers.sense_check_threshold` (default 0.80).
   - If share < threshold: emit loud warning:
     ```
     ⚠️  SENSE-CHECK FAILED
     Only X% of your Closed-Won landed in T1/T2 (threshold: Y%).
     Your algorithm does not recognize your own best customers.
     Before trusting data/accounts-scored/tiered.csv:
       - Review which Closed-Won companies were misclassified (see data/accounts-scored/closed-won-sense-check.csv)
       - Re-weight rules in scoring/weights.yaml
       - Consider hard-coding rules for edge cases
       - Re-run this skill
     ```
   - Write `data/accounts-scored/closed-won-sense-check.csv` with each Closed-Won row, its computed score, its tier, and top_rules. This is the audit trail.
   - If share >= threshold: print `"Sense-check passed: X% of Closed-Won in T1/T2."`

## Anti-patterns

- Do NOT silently rewrite `scoring/weights.yaml` on re-runs. User owns that file.
- Do NOT skip the sense-check.
- Do NOT produce a single-tier output. Tiers are the point.
- Do NOT call external APIs inside `scoring/rules.py` — deterministic rules are local Python only. External calls belong in `rules.md`.
- Do NOT pretend LLM rules succeeded when they failed silently. Cache errors and surface them.

## When done (run mode)

Print:
```
Scored N accounts. Distribution:
  T1: A  (B%)
  T2: C  (D%)
  T3: E  (F%)
  T4: G  (H%)
Sense-check: [PASSED / FAILED with X% vs threshold Y%]
Output: data/accounts-scored/tiered.csv
```
