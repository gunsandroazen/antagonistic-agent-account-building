---
name: pattern-recognition
description: Use when the user has an enriched Closed-Won CSV in data/closed-won/ and wants to surface candidate patterns (location, headcount, ownership, funding, tech stack, HQ, etc.) that might define their best-fit customer. Outputs candidate patterns as JSON to data/patterns/candidates.json. Does NOT decide which patterns matter — that's the antagonist's job.
---

# Pattern Recognition Skill

## Your role

Surface every candidate pattern in the Closed-Won CSV. Be noisy. Overproduction is expected here — the antagonist skill will cut it down.

## Preconditions

1. Read `data/closed-won/`. It must contain **exactly one** `.csv` file. If zero or multiple, STOP and tell the user which state they're in.
2. Read the CSV header and a sample of rows. The file must have ≥20 rows and ≥5 columns. If not, STOP and tell the user the CSV is too small.

## How to analyze

For every column:
- Compute cardinality (distinct values), null rate, and top-10 values by frequency.
- For numeric columns, compute min/max/median and suggest natural bands (quartiles, or semantically meaningful bands like "headcount 1-10, 11-50, 51-200, ...").
- For text-heavy columns (descriptions, notes, free-text), extract recurring themes (use your own judgment; don't call external APIs).

Then surface interaction effects where obvious — e.g., `hq_city=NYC ∧ funding_stage=Series B` showing up more than either alone would predict.

**Bias toward breadth.** Surface dozens of patterns, even hundreds if the data supports it. Do not skip a column because it "looks low-signal." The antagonist decides what matters.

## Output contract

Write `data/patterns/candidates.json` with this structure:

```json
{
  "source_file": "data/closed-won/<filename>.csv",
  "row_count": 847,
  "column_count": 42,
  "patterns": [
    {
      "id": "hq_nyc",
      "dimension": "hq_city",
      "claim": "63% of Closed-Won are HQ'd in NYC",
      "evidence": {
        "match_rate": 0.63,
        "sample_matches": ["Acme Corp", "Beta Inc", "Gamma LLC"],
        "total_matches": 534
      },
      "hypothesis": "NYC proximity may correlate with fit — possibly sales-team geography, possibly real signal"
    }
  ]
}
```

Every pattern MUST have: `id` (slug), `dimension` (source column or interaction), `claim` (one sentence), `evidence` (quantitative), `hypothesis` (what it might mean — this is genuinely a guess, label it as such).

## Anti-patterns

- Do NOT rank, score, or filter patterns. That's the antagonist's job.
- Do NOT write `data/target-description.md`. That's the loop's job.
- Do NOT edit anything in `scoring/`. That's the account-scoring skill's job.
- Do NOT skip columns because you think they won't matter.
- Do NOT say "more analysis needed" — surface what you find, let the antagonist argue.

## When done

Print a one-line summary to the user: `"Surfaced N candidate patterns across M dimensions. Written to data/patterns/candidates.json. Run antagonist next (or pattern-antagonist-loop for the full fight)."`
