---
name: pattern-recognition
description: Use when the user has an enriched Closed-Won CSV in data/closed-won/ and wants to surface candidate patterns that might define their best-fit customer. Performs column-level profiling, value-level frequency analysis, interaction detection, time-weighted analysis, and free-text theme extraction. Outputs rich candidate patterns with statistical evidence (match rates, baselines, lift, effect size) to data/patterns/candidates.json. Never filters, scores, or decides which patterns matter — that is the antagonist's job. Biased toward breadth; the antagonist prunes.
---

# Pattern Recognition Skill

## Your role

Surface every candidate pattern in the Closed-Won CSV with statistical evidence strong enough for the antagonist to prosecute or defend. Be noisy. Overproduction is expected here — the antagonist skill will cut it down.

You are not reasoning about fit. You are surfacing *signal candidates* with enough evidence that a skeptical reader could audit each claim.

---

## Preconditions (hard-stop checks)

1. **Exactly one CSV in `data/closed-won/`.** If zero or multiple, STOP. Tell the user the exact state of the directory.
2. **Row and column floor.** ≥20 rows and ≥5 columns. Below that, STOP — there's no statistical air for pattern claims.
3. **If `data/closed-won/.data-audit.json` exists**, read it first. If the audit flagged `severity: critical` issues (e.g., >30% duplicate domains, >50% nulls in every column), STOP and instruct the user to resolve them before re-running.
4. **If `data/closed-won/.data-audit.json` does not exist**, invoke the `data-audit` skill first to produce it. Then continue.

---

## Tooling

Prefer **Python with pandas** (`import pandas as pd`). Every Python environment likely to be in scope for Claude Code has pandas. If pandas is unavailable, fall back to the `csv` stdlib — but warn the user and use simpler statistics.

For any statistical test beyond frequencies, use `scipy.stats` if available (chi-square, Fisher's exact). If scipy is unavailable, compute **lift** and **confidence intervals via Wilson score** manually — they're cheap and sufficient.

Never call external APIs. This skill is fully local.

---

## Pipeline

### Stage 1 — Load and classify columns

1. Read the CSV with `pd.read_csv(..., dtype=str, keep_default_na=True)`. Parsing strings first avoids pandas' "int vs float vs nan" surprises.
2. Classify each column into one of: `numeric_continuous`, `numeric_discrete`, `categorical_low_card` (<20 distinct), `categorical_high_card` (20-500 distinct), `categorical_very_high_card` (>500 — often free text masquerading), `text_free`, `date`, `boolean`, `list_like` (comma-joined or pipe-joined strings like tech stacks), `unknown`.
3. Coerce types where safe. Headcount text like `"120"` → int. Funding text like `"$2.4M"` or `"2400000"` → numeric. Dates to `datetime`. If coercion fails, keep as string and note it.
4. **Compute time weights.** If the CSV has a `closed_won_date` or similar date column, compute a recency weight for each row: `w_i = exp(-days_ago / half_life)` with `half_life = 365` days. All frequency stats downstream can use either raw or weighted counts — **surface both** where they disagree by >10 percentage points. If no date column, skip time-weighting and note it.

### Stage 2 — Per-column profiling

For **every** column, record in the candidates output:
- `cardinality`: distinct value count
- `null_rate`: fraction of rows with null/empty
- `top_values`: top 10 values by frequency (weighted + unweighted)
- For numeric: `min`, `max`, `median`, `mean`, `p25`, `p75`, `iqr`, `stdev`
- For date: `earliest`, `latest`, `span_days`
- For list-like: explode the lists and profile the element frequency (each tech in a tech-stack column becomes its own frequency entry)

Do NOT emit a pattern per column profile — profiles are context for the patterns, not patterns themselves. Store column profiles under `column_profiles` in the output.

### Stage 3 — Value-level patterns

For every `categorical_low_card` column and every list-like element:
- Compute `match_rate` = weighted share of rows where value matches.
- Compute `total_matches` and `total_rows`.
- Add a pattern with `evidence.match_rate`, `evidence.total_matches`, `evidence.sample_row_ids` (see Provenance below).

For every `numeric_continuous` column:
- Propose 3-5 candidate bands using both quartiles and semantically sensible cuts (for headcount: 1-10, 11-50, 51-200, 201-500, 501-1000, 1001+; for ARR: $0-500k, 500k-1M, 1M-5M, 5M+).
- Emit one pattern per band with match rate + evidence.

For every `date` column:
- Emit patterns for recent-cohort skew (e.g., "70% of Closed-Won closed in the last 12 months") and seasonality if present.

For `categorical_high_card` columns (industries, cities):
- Only emit patterns for values with `total_matches >= 3` AND `match_rate >= 0.05`. Below that, the sample is too small — note in the profile, don't surface as a pattern.

For `text_free` columns:
- Extract recurring themes using your own judgment (no external APIs). Examples: "mentions 'AI' in company description", "uses word 'platform' in tagline". Emit each theme as a pattern with its match rate.

### Stage 4 — Interaction patterns

For every pair of low-cardinality categorical columns (A, B) where both have match rates individually ≥ 0.10:
- Compute the joint match rate `P(A ∧ B)`.
- Compute expected joint rate under independence: `P(A) * P(B)`.
- Compute **lift** = `P(A ∧ B) / (P(A) * P(B))`.
- If `lift >= 1.5` AND `P(A ∧ B) >= 0.15`, emit as an interaction pattern.

For triples, only if a pair already showed lift ≥ 2.0 — limit combinatorial explosion.

Emit list-like interactions similarly (e.g., `Segment ∈ tech_stack ∧ Snowflake ∈ tech_stack`).

### Stage 5 — Disqualifiers (negative patterns)

For every value present in the broader B2B population but absent or rare in Closed-Won (match rate ≤ 0.02 AND sample ≥ 20), emit as a **negative pattern**. These become disqualifier candidates downstream.

Example: `ownership_type=Public` appears in ~15% of the broader B2B universe but 0% of Closed-Won → disqualifier candidate.

Since you don't have the broader population locally, mark these as `"population_baseline": null, "requires_antagonist_base_rate_check": true`. The antagonist will prosecute whether these are real disqualifiers or artifacts of sample size.

---

## Statistical evidence per pattern

Every emitted pattern MUST carry:
- `match_rate` (weighted) and `match_rate_unweighted` if they differ by ≥5pp
- `total_matches` (absolute row count)
- `confidence_interval_95`: Wilson score interval `[low, high]` computed as:
  ```
  z = 1.96
  p = total_matches / total_rows
  n = total_rows
  denom = 1 + z**2/n
  center = (p + z**2/(2*n)) / denom
  half = z*sqrt((p*(1-p) + z**2/(4*n))/n) / denom
  CI = [center - half, center + half]
  ```
- `population_baseline`: null for v1. The antagonist will fill this in by prosecuting. Leave the field present so downstream tools can tell the difference between "no baseline" and "missing field."
- `sample_row_ids`: list of up to 10 row indices (0-indexed) so the antagonist and humans can verify the pattern by pulling actual rows from the CSV.

---

## Segmentation (optional, high-value)

If the CSV has a column that looks like a segment key (`segment`, `offering`, `product_line`, `customer_type`, `tier`), OR if the user has told you to segment, run the pipeline **per segment** and emit one candidates file per segment:

- `data/patterns/candidates.json` — overall
- `data/patterns/candidates.segment-<slug>.json` — per segment

Segmentation is surfaced but not forced — overall is always written. The user or the orchestrator decides which to feed the antagonist.

If you detect heterogeneity (e.g., a column splits Closed-Won into groups with very different firmographic profiles), add a top-level `segmentation_recommendation` block to `candidates.json` explaining what you saw.

---

## Output contract

Write `data/patterns/candidates.json` with this exact structure:

```json
{
  "generated_at": "2026-04-23T14:32:01Z",
  "source_file": "data/closed-won/foo.csv",
  "row_count": 847,
  "weighted_row_count": 842.3,
  "column_count": 42,
  "time_weighting": {
    "applied": true,
    "date_column": "closed_won_date",
    "half_life_days": 365
  },
  "column_profiles": {
    "hq_city": {
      "type": "categorical_high_card",
      "cardinality": 87,
      "null_rate": 0.02,
      "top_values": [
        { "value": "New York", "count": 412, "weighted_count": 398.1, "share": 0.49 },
        { "value": "Brooklyn", "count": 88, "weighted_count": 85.4, "share": 0.10 }
      ]
    }
  },
  "patterns": [
    {
      "id": "hq_nyc_metro",
      "kind": "value",
      "dimension": "hq_city",
      "claim": "63% of Closed-Won are HQ'd in the NYC metro (NYC + Brooklyn + Jersey City)",
      "evidence": {
        "match_rate": 0.63,
        "match_rate_unweighted": 0.61,
        "total_matches": 534,
        "total_rows": 847,
        "confidence_interval_95": [0.598, 0.661],
        "population_baseline": null,
        "requires_antagonist_base_rate_check": true,
        "sample_row_ids": [2, 7, 11, 14, 19, 23, 31, 44, 52, 68]
      },
      "hypothesis": "NYC proximity may correlate with fit — possibly sales-team geography, possibly real signal"
    },
    {
      "id": "segment_snowflake_dbt_together",
      "kind": "interaction",
      "dimensions": ["tech_stack contains Segment", "tech_stack contains Snowflake", "tech_stack contains dbt"],
      "claim": "42% of Closed-Won have all three of Segment+Snowflake+dbt",
      "evidence": {
        "match_rate": 0.42,
        "total_matches": 356,
        "total_rows": 847,
        "confidence_interval_95": [0.387, 0.454],
        "expected_under_independence": 0.18,
        "lift": 2.33,
        "sample_row_ids": [1, 6, 17, 22, 29, 38, 47, 55, 61, 73]
      },
      "hypothesis": "Modern-data-stack maturity proxy; may be more predictive than any single tech"
    },
    {
      "id": "ownership_public_absent",
      "kind": "negative",
      "dimension": "ownership_type",
      "claim": "0% of Closed-Won are publicly traded",
      "evidence": {
        "match_rate": 0.00,
        "total_matches": 0,
        "total_rows": 847,
        "confidence_interval_95": [0.000, 0.004],
        "population_baseline": null,
        "requires_antagonist_base_rate_check": true,
        "sample_row_ids": []
      },
      "hypothesis": "Likely a real disqualifier — public-company buying cycles differ — but absence may be a sample-size artifact. Antagonist must adjudicate."
    }
  ],
  "segmentation_recommendation": {
    "detected_segment_columns": ["offering"],
    "heterogeneity_flag": false,
    "note": "Offering column has 2 values (Starter, Pro) but firmographic profiles overlap — segmentation not required."
  },
  "self_diagnostics": {
    "columns_coerced_to_numeric": ["headcount", "estimated_arr_usd"],
    "columns_coerced_to_date": ["closed_won_date"],
    "columns_kept_as_string_despite_numeric_shape": [],
    "columns_with_over_50pct_null": [],
    "suspected_free_text_columns": ["company_description"],
    "warnings": []
  }
}
```

Every `id` must be a unique slug. Every `kind` must be one of: `value`, `numeric_band`, `interaction`, `negative`, `temporal`, `text_theme`.

---

## Breadth expectations

For a typical 500-5000 row enriched Closed-Won CSV with 20-60 columns, expect to emit **80-400 candidate patterns**. If you emit fewer than 40, you are under-surfacing — go back and look harder at interactions, bands, and text themes. If you emit more than 600, you are over-surfacing — dedupe semantically-equivalent patterns (e.g., `hq_city=New York` and `hq_metro=NYC Metro` are near-duplicates; pick one).

---

## Anti-patterns

- Do NOT rank, score, or filter patterns for fit. That is the antagonist's job.
- Do NOT write `data/target-description.md`. That is the loop's job.
- Do NOT edit anything in `scoring/`.
- Do NOT skip columns because they "look low-signal."
- Do NOT say "more analysis needed." Surface what you find; let the antagonist prosecute.
- Do NOT call external APIs or do web research. This skill is offline.
- Do NOT invent population baselines you don't have evidence for. Leave `population_baseline: null` and flag for the antagonist.

---

## When done

Print a summary to the user:

```
Pattern recognition complete.
  Source: data/closed-won/<filename>.csv (<N> rows × <M> cols, <W>% recency-weighted)
  Surfaced: <P> candidate patterns
    - Value patterns: <a>
    - Numeric band patterns: <b>
    - Interaction patterns: <c>
    - Negative/disqualifier candidates: <d>
    - Text-theme patterns: <e>
    - Temporal patterns: <f>
  Columns coerced: <list>
  Self-diagnostic warnings: <count>

Written to data/patterns/candidates.json.
Next: run `antagonist` to prosecute, or `pattern-antagonist-loop` for the full fight.
```
