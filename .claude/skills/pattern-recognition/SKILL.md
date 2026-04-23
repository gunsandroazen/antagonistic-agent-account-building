---
name: pattern-recognition
description: Universal pattern discovery for any CSV. Ingests a CSV from a known path, reads it column by column, profiles every column by inferred type, analyzes value distributions, extracts numeric bands, list-element frequencies, text themes, temporal trends, and interaction effects across column pairs. Emits a rich, exhaustive JSON of candidate patterns with statistical evidence (match rate, Wilson CI, lift over independence, sample provenance) that downstream skills (especially antagonist) can prosecute. Never judges relevance, never filters, never decides which patterns matter — just surfaces what the data says. Biased toward breadth. Works on ANY tabular data, not just Closed-Won.
---

# Pattern Recognition Skill

## Your role

You are a **universal pattern discovery engine** for tabular data. Given any CSV, you read it column by column, understand each column's type and distribution, surface every pattern the data supports, and write them to a JSON artifact.

You do NOT:
- Judge whether a pattern is "good" or "relevant"
- Filter based on what you think the user is looking for
- Assume the CSV is about customers, companies, or anything specific
- Apply domain knowledge to pick patterns

You DO:
- Read every column
- Profile every value
- Compute every frequency
- Surface every interaction with meaningful lift
- Label every pattern with auditable evidence

The **antagonist** skill downstream decides which patterns matter. Your job is to give it everything to work with.

---

## Input contract

The skill is invoked against a single CSV path. Resolution order:

1. If the user provided an explicit path, use it.
2. Else look in `data/closed-won/` for exactly one `.csv`. If found, use it.
3. Else look in the current working directory for the most recently modified `.csv`.
4. Else STOP with a message asking for a path.

**This skill is NOT tied to Closed-Won data.** The repo's primary use case is Closed-Won analysis, but this skill accepts ANY CSV — survey responses, email logs, transaction data, whatever. The pattern-antagonist-loop is what specializes it to Closed-Won via how it prompts the antagonist.

---

## Preconditions (hard-stop checks)

1. **CSV exists and is readable.** Attempt UTF-8, fall back to latin-1, report encoding used.
2. **Row and column floor.** ≥20 data rows and ≥2 columns. Below that, STOP — statistical claims need air.
3. **Data audit.** If the CSV path is `data/closed-won/<file>.csv` and `data/closed-won/.data-audit.json` exists, honor it (refuse if `severity: critical`). For CSVs outside that path, auditing is optional — proceed but note it in self_diagnostics.

---

## Tooling

- **Python + pandas preferred** (`pd.read_csv`). Parse all values as strings first (`dtype=str, keep_default_na=False, na_values=["", "NA", "N/A", "null", "-", "None"]`) to avoid pandas' eager type coercion swallowing information.
- Fall back to stdlib `csv` + manual statistics if pandas is unavailable.
- For confidence intervals, compute Wilson score interval manually (formula below). No external libraries needed.
- Never call external APIs. Fully local.

---

## Pipeline

### Stage 0 — Load and meta

1. Read the CSV. Record: encoding, separator (sniff if not comma), row count, column count, header.
2. Record any structural issues (rows with wrong column count, BOM, trailing empty lines).
3. Determine the output path: if the CSV is under `data/closed-won/`, write to `data/patterns/candidates.json`. Otherwise, write to the same directory as the CSV with the suffix `.patterns.json`.

### Stage 1 — Read column by column, infer type for each

For every column, iterate through its values and infer type. Do not trust the column name — use the actual values. For each column, classify into exactly one:

| Type | Rule |
|---|---|
| `boolean` | distinct non-null values ⊆ `{true, false, yes, no, 1, 0, y, n, t, f}` (case-insensitive) |
| `numeric_continuous` | ≥90% of non-null values coerce to float AND cardinality > 20 |
| `numeric_discrete` | ≥90% coerce to int AND cardinality ≤ 20 |
| `date` | ≥90% parse as ISO date / common formats AND cardinality > 5 |
| `categorical_low` | cardinality between 2 and 19, non-numeric |
| `categorical_mid` | cardinality between 20 and 500 |
| `categorical_high` | cardinality between 500 and row_count × 0.8 |
| `identifier` | cardinality ≈ row_count (≥95%) — likely IDs, names, domains |
| `list_like` | values contain a consistent separator (`,`, `;`, `|`, ` / `) — each cell is a list |
| `text_free` | average token count > 10 AND cardinality > 500 |
| `json_like` | values parse as JSON objects/arrays |
| `empty` | null rate ≥ 95% — skip pattern extraction |
| `unknown` | doesn't fit any of the above |

Record the inference in `column_profiles[col]['inferred_type']` along with confidence (`high`, `medium`, `low`) and why. Record ambiguous cases (e.g., a column that's 70% numeric but 30% text) explicitly.

Record type-specific profile data per column:
- **numeric:** min, max, median, mean, p25, p75, p95, stdev, null rate.
- **date:** earliest, latest, span_days, null rate, monthly histogram.
- **categorical:** cardinality, top-20 values with counts and shares, null rate.
- **list_like:** separator detected, element cardinality (distinct elements across all cells), top-20 elements with document-frequency (how many rows contain each).
- **text_free:** avg/median token count, cardinality, null rate. Do NOT dump sample text into the output — it balloons the file.
- **identifier / empty:** note and move on. No patterns extracted.

### Stage 2 — Time weighting (if a date column is present)

If exactly one column is classified as `date` and has <20% null rate, use it as the event timestamp for time weighting. Compute a recency weight per row: `w_i = exp(-days_ago / half_life)` with `half_life = 365`. Every frequency / match-rate statistic downstream reports BOTH weighted and unweighted values if they differ by ≥5 percentage points. If no date column, skip and note.

If multiple date columns, pick the one whose name best matches `closed`, `won`, `created`, `event`, `transaction`, `signup`. If no clear match, pick the one with the latest max value (most recent data is usually the event we care about). Log the choice.

### Stage 3 — Per-column pattern extraction

For every column, based on its inferred type:

**boolean / categorical_low:**
- Emit one pattern per value: `{column} = {value}`, match_rate = share of rows with that value.

**categorical_mid:**
- Emit patterns for the top-50 values by frequency, provided `total_matches >= 3` AND `match_rate >= 0.02`.
- Also emit rollup patterns if the column name or values suggest a natural hierarchy (e.g., `hq_city` rolls up to `hq_state` if another column has that).

**categorical_high:**
- Emit patterns only for values with `total_matches >= 5` AND `match_rate >= 0.05`.
- If the column looks like a free-text classification (long strings, variable casing), also emit n-gram patterns: most common 1-grams, 2-grams, 3-grams across values.

**numeric_continuous:**
- Emit patterns for 4 candidate binnings:
  1. **Quartile bins:** `[min, p25]`, `[p25, median]`, `[median, p75]`, `[p75, max]`.
  2. **Log-scaled bins:** if the range spans >2 orders of magnitude, use `[1, 10, 100, 1000, 10000, 100000, 1000000, 10000000+]`-style bins.
  3. **Natural-number bins:** headcount-style — `[1-10, 11-50, 51-200, 201-500, 501-1000, 1001-5000, 5001+]`. Detect applicability: if column name matches `/headcount|employees|size|staff/i` OR values are all positive integers with p95 < 100000.
  4. **Round-money bins:** if column name matches `/revenue|arr|mrr|funding|price|amount|usd|dollars/i` OR values look like money: `[$0-100k, $100k-500k, $500k-1M, $1M-5M, $5M-25M, $25M-100M, $100M+]`.
- Emit a pattern for each bin with match_rate and count. Use whichever binning produces bins with match rates between 0.05 and 0.60 (most informative).

**numeric_discrete:**
- Emit one pattern per distinct value (it's discrete with ≤20 values).

**date:**
- Emit patterns for:
  - Recent cohort skew: `70% of events in the last 12 months`.
  - Year-over-year buckets.
  - Month-of-year patterns (seasonality): `Closed in Q1 / Q2 / Q3 / Q4`.
  - Day-of-week patterns if the span is >30 days.

**list_like:**
- Explode the lists. Emit one pattern per element with `match_rate = share of rows whose list contains this element`.
- Emit for top-50 elements with `total_matches >= 3`.

**text_free:**
- Extract themes using heuristics (you, the LLM running this skill, do this directly — no external NLP libraries):
  - Most common 1-grams (after basic stopword filtering — `the`, `a`, `of`, etc.).
  - Most common 2-grams and 3-grams.
  - Recurring themes from reading the actual values: buzzwords, industry terms, positioning language.
- Emit each as a pattern: `{column} contains "{phrase}"`, match_rate = fraction of rows containing the phrase (case-insensitive substring).
- Cap at top-30 themes per text column to avoid explosion.

**identifier / empty / json_like / unknown:**
- Do not emit patterns. Note in self_diagnostics.

### Stage 4 — Interaction discovery across column pairs

For every pair of columns (A, B) where BOTH have at least one value-pattern with match_rate ≥ 0.10, compute interactions:

1. **Categorical × categorical:** For the top-10 values of A and top-10 values of B, compute joint match rate `P(A=a ∧ B=b)`. Compare to expected under independence `P(A=a) × P(B=b)`. Emit as an interaction pattern if:
   - `lift = P(joint) / P(expected) >= 1.5`
   - `P(joint) >= 0.05`
   - `joint_matches >= 5`

2. **Numeric-band × categorical:** Same logic but with the numeric bins from Stage 3 instead of raw values.

3. **List-element × list-element** (same or different list columns): detect tech-stack-style co-presence. E.g., `"Segment" ∈ tech_stack ∧ "Snowflake" ∈ tech_stack`. Use the same lift + support rules.

4. **Triple interactions:** only if a pair already showed lift ≥ 2.0 AND joint match rate ≥ 0.15. Limit combinatorial explosion.

Cap total interaction patterns at **300** to keep the JSON manageable. If more candidates exist, keep the ones with highest lift × joint_match_rate product.

### Stage 5 — Negative / absence patterns

For every categorical column (any cardinality), identify values that are **conspicuously absent** — present in small amounts or zero, where an observer would expect more:

- Heuristic: if a value appears in <2% of rows AND has `total_matches < 5` AND the column has ≥3 other values with match rate >10%, this is a candidate "near-absent" pattern.
- These are emitted as `kind: "negative"` with match_rate recorded AND a note that the antagonist must prosecute whether absence is real signal or a sample-size artifact.

### Stage 6 — Cross-column derived patterns

Where the data supports it, derive composite patterns:

- If the CSV has a date column AND another relevant column, emit time-sliced patterns: "In the last 12 months, {pattern} has match rate X; in the prior 12 months, Y."
- If a numeric column has suspicious clustering (bimodal distribution), emit a "two populations" pattern flagging that downstream analysis may want to segment.
- If columns A and B appear to be highly correlated (A is a near-duplicate of B), emit a `data_quality_note` rather than patterns for both — helps the antagonist avoid double-counting signal.

### Stage 7 — Output

Write the JSON output. Exact schema:

```json
{
  "generated_at": "ISO-8601 timestamp",
  "source_file": "absolute or repo-relative path",
  "source_meta": {
    "encoding": "utf-8",
    "separator": ",",
    "row_count": 847,
    "column_count": 42,
    "bom": false,
    "structural_issues": []
  },
  "time_weighting": {
    "applied": true,
    "date_column": "closed_won_date",
    "half_life_days": 365,
    "weighted_row_count": 712.4
  },
  "column_profiles": {
    "hq_city": {
      "inferred_type": "categorical_mid",
      "type_inference_confidence": "high",
      "cardinality": 87,
      "null_rate": 0.02,
      "top_values": [
        { "value": "New York", "count": 412, "weighted_count": 398.1, "share": 0.49, "weighted_share": 0.56 },
        { "value": "Brooklyn", "count": 88, "weighted_count": 85.4, "share": 0.10, "weighted_share": 0.12 }
      ]
    },
    "headcount": {
      "inferred_type": "numeric_continuous",
      "type_inference_confidence": "high",
      "min": 3, "max": 8400, "median": 142, "mean": 287.4,
      "p25": 58, "p75": 310, "p95": 1240,
      "null_rate": 0.03,
      "binning_chosen": "natural_number",
      "binning_reason": "column name matches headcount pattern; values are positive integers"
    },
    "tech_stack": {
      "inferred_type": "list_like",
      "separator": ",",
      "element_cardinality": 187,
      "top_elements": [
        { "element": "Segment", "document_frequency": 712, "share": 0.85 },
        { "element": "Snowflake", "document_frequency": 601, "share": 0.71 }
      ]
    }
  },
  "patterns": [
    {
      "id": "hq_city_eq_new_york",
      "kind": "value",
      "column": "hq_city",
      "claim": "hq_city = 'New York' in 49% of rows (56% weighted)",
      "evidence": {
        "match_rate": 0.56,
        "match_rate_unweighted": 0.49,
        "total_matches": 412,
        "total_rows": 847,
        "confidence_interval_95": [0.456, 0.523],
        "sample_row_ids": [0, 2, 7, 11, 14, 19, 23, 31, 44, 52]
      }
    },
    {
      "id": "headcount_band_51_200",
      "kind": "numeric_band",
      "column": "headcount",
      "binning_scheme": "natural_number",
      "claim": "headcount in [51, 200] covers 38% of rows (41% weighted)",
      "evidence": {
        "match_rate": 0.41,
        "match_rate_unweighted": 0.38,
        "total_matches": 322,
        "total_rows": 847,
        "confidence_interval_95": [0.346, 0.413],
        "sample_row_ids": [1, 4, 9, 15, 22, 28, 33, 41, 48, 55]
      }
    },
    {
      "id": "tech_stack_contains_segment",
      "kind": "list_element",
      "column": "tech_stack",
      "element": "Segment",
      "claim": "tech_stack contains 'Segment' in 85% of rows",
      "evidence": {
        "match_rate": 0.85,
        "total_matches": 712,
        "total_rows": 847,
        "confidence_interval_95": [0.825, 0.873],
        "sample_row_ids": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
      }
    },
    {
      "id": "interaction_segment_and_snowflake_and_dbt",
      "kind": "interaction",
      "columns": ["tech_stack", "tech_stack", "tech_stack"],
      "components": ["tech_stack contains Segment", "tech_stack contains Snowflake", "tech_stack contains dbt"],
      "claim": "All three of Segment + Snowflake + dbt present in 42% of rows; expected under independence 18%",
      "evidence": {
        "match_rate": 0.42,
        "expected_under_independence": 0.18,
        "lift": 2.33,
        "total_matches": 356,
        "total_rows": 847,
        "confidence_interval_95": [0.387, 0.454],
        "sample_row_ids": [1, 6, 17, 22, 29, 38, 47, 55, 61, 73]
      }
    },
    {
      "id": "text_theme_homepage_mentions_ai_native",
      "kind": "text_theme",
      "column": "company_description",
      "phrase": "ai-native",
      "match_rate": 0.12,
      "total_matches": 102,
      "total_rows": 847,
      "claim": "company_description contains 'ai-native' in 12% of rows"
    },
    {
      "id": "temporal_recent_12mo_cohort",
      "kind": "temporal",
      "column": "closed_won_date",
      "claim": "70% of events are in the last 12 months",
      "evidence": { "match_rate": 0.70, "total_matches": 593, "total_rows": 847 }
    },
    {
      "id": "negative_ownership_type_public_absent",
      "kind": "negative",
      "column": "ownership_type",
      "claim": "ownership_type = 'Public' appears in 0% of rows (0 of 847)",
      "evidence": {
        "match_rate": 0.00,
        "total_matches": 0,
        "total_rows": 847,
        "confidence_interval_95": [0.000, 0.004],
        "sample_row_ids": []
      },
      "note": "Conspicuously absent — antagonist must prosecute whether this is signal or sample size"
    }
  ],
  "data_quality_notes": [
    {
      "type": "near_duplicate_columns",
      "columns": ["hq_city_name", "hq_city"],
      "similarity": 0.99,
      "note": "These two columns appear to encode the same information."
    }
  ],
  "self_diagnostics": {
    "columns_analyzed": 42,
    "columns_skipped": 2,
    "skip_reasons": {
      "identifier": ["crm_id", "internal_uuid"],
      "empty": []
    },
    "columns_with_ambiguous_type": [],
    "total_patterns_emitted": 324,
    "patterns_by_kind": {
      "value": 187,
      "numeric_band": 23,
      "list_element": 47,
      "interaction": 48,
      "text_theme": 11,
      "temporal": 4,
      "negative": 4
    },
    "time_weighting_applied": true,
    "warnings": []
  }
}
```

Every pattern MUST have: unique `id` (slug), `kind`, a human-readable `claim`, `evidence` with `match_rate`, `total_matches`, `total_rows`, `confidence_interval_95`, and `sample_row_ids` (up to 10 zero-indexed row numbers for provenance). Interactions additionally require `expected_under_independence` and `lift`.

---

## Wilson score confidence interval

When pattern-recognition needs a 95% CI on a match rate, use Wilson score (robust for small samples):

```
z = 1.96
p = total_matches / total_rows
n = total_rows
denom = 1 + z**2 / n
center = (p + z**2 / (2*n)) / denom
half = z * sqrt((p*(1-p) + z**2 / (4*n)) / n) / denom
CI = [max(0, center - half), min(1, center + half)]
```

Apply to every pattern with a match_rate.

---

## Breadth expectations

For a 500-5000 row CSV with 20-60 columns: expect **150-600 candidate patterns**. Fewer than 60 = under-surfaced (look harder at interactions and text themes). More than 800 = over-surfaced (dedupe near-equivalents, cap interaction emission).

For smaller CSVs (20-500 rows): expect 30-200 patterns.

For wide CSVs (>100 columns): pattern count scales roughly linearly — don't artificially cap it.

---

## Anti-patterns

- Do NOT rank patterns by "importance" or "relevance." Emission order is by column, not by judgment.
- Do NOT filter out patterns because they "feel obvious" or "feel uninteresting." The antagonist decides.
- Do NOT assume the CSV is about any particular domain. Work from what the columns and values say.
- Do NOT edit `data/target-description.md`, `scoring/*`, or anything outside the patterns output path.
- Do NOT make up data. If you can't compute something (missing dependency, parse failure), note it in self_diagnostics and move on.
- Do NOT invent pattern kinds beyond: `value`, `numeric_band`, `list_element`, `interaction`, `text_theme`, `temporal`, `negative`.
- Do NOT inject domain assumptions (e.g., "tech stack should be a list_like") — let type inference do the work.

---

## When done

Print:

```
Pattern discovery complete.
  Source: <path> (<N> rows × <M> cols, encoding <enc>)
  Time-weighted: <yes/no, column used if yes>
  Columns analyzed: <N_analyzed> (<N_skipped> skipped — see self_diagnostics)
  Patterns emitted: <P>
    value: <a>     numeric_band: <b>    list_element: <c>
    interaction: <d>    text_theme: <e>    temporal: <f>    negative: <g>
  Data quality notes: <Q>

Output: <path>/candidates.json  (or <path>.patterns.json if outside data/closed-won/)
Next: run `antagonist` to prosecute which patterns matter.
```
