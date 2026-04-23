---
name: data-audit
description: Use before running pattern-recognition, or whenever the user drops a new Closed-Won CSV into data/closed-won/. Audits the CSV for the garbage-in problems that quietly corrupt everything downstream — duplicate domains, mixed encodings, free-text in numeric columns, extreme null rates, suspicious cardinality, PII that should not be in the repo, and structural problems (trailing commas, inconsistent row lengths, BOM markers). Writes data/closed-won/.data-audit.json with a severity classification (clean/warnings/critical) and a per-column diagnosis. Pattern-recognition will refuse to run if severity=critical.
---

# Data Audit Skill

## Your role

Catch data quality problems before they pollute the pattern-antagonist loop. Garbage inputs produce agreeable-looking outputs that read fine but encode real bugs. You are the first gate.

You are fast, strict, and loud. Warnings are visible; critical issues block downstream work.

---

## Preconditions

1. `data/closed-won/` contains at least one `.csv` file. If zero, STOP.
2. If multiple CSVs, audit each one and write one `.data-audit.<filename>.json` per file.

---

## Tooling

Python + pandas. If pandas unavailable, `csv` stdlib. Everything runs locally.

---

## Checks to perform

### Structural

- **Encoding:** attempt UTF-8 first, then latin-1 as fallback. If file has a BOM, note it.
- **Row length consistency:** if any row has ≠ header column count, flag as critical.
- **Trailing empty lines / trailing commas:** note.
- **Header duplicates:** `[name, name, funding]` has a duplicate header — flag as critical.
- **Header whitespace:** `" headcount"` vs `"headcount"` — flag as warning; normalize downstream.

### Row-level

- **Total row count:** if < 20, flag as critical (pattern-recognition won't run meaningfully).
- **Duplicate detection:** if a `domain` or `company_domain` or `website` column exists, compute duplicate-domain rate. Normalize (lowercase, strip `www.`, strip trailing slash) before dedup. If duplicate rate > 5%, flag warning; > 30%, flag critical.
- **Completely-empty rows:** flag.

### Column-level

For each column, compute:
- Null rate (including `""`, `"null"`, `"N/A"`, `"-"` treated as null).
- Cardinality.
- Inferred type vs declared content (e.g., a column named `headcount` with values like `"50-100"` and `"~200"` can't be coerced to int without work).
- Presence of likely PII:
  - Email pattern (`\S+@\S+\.\S+`) in any text column not named `email`/`contact`/similar → warning, PII-in-unexpected-column.
  - Phone pattern, SSN-like, credit-card-like → critical.

### Semantic

- **Date columns that look like dates but have >10% un-parseable values:** warning.
- **Currency columns with mixed formats** (`"$2.4M"` vs `"2400000"` vs `"2,400,000"`): warning with normalization recipe.
- **Boolean-ish columns with 3+ distinct values** (`yes/no/maybe/true/false/1/0`): warning.
- **Free text columns >200 chars average:** flag as potential `text_free` for pattern-recognition.
- **Any column with cardinality = row_count:** likely a unique identifier (not useful for patterns). Flag informationally.
- **Any column with cardinality = 1:** useless (everyone has the same value). Flag informationally.

### PII + compliance

If the CSV appears to contain direct personal identifiers (`first_name`, `last_name`, `email`, `phone`, `mobile` headers), emit a prominent warning: *"This CSV contains personal data. Confirm it is sanitized before committing to any git remote. `data/` is gitignored but fork-level `.gitignore` changes can expose it."*

---

## Severity classification

Compute overall severity as the MAX of all individual findings:

- **`clean`** — all checks passed or informational only.
- **`warnings`** — at least one warning, no critical. Pattern-recognition will run but note the warnings in its self_diagnostics.
- **`critical`** — at least one critical finding. Pattern-recognition must refuse to run until resolved.

---

## Output contract

Write `data/closed-won/.data-audit.json` (one per CSV; use `.data-audit.<stem>.json` if multiple CSVs):

```json
{
  "generated_at": "2026-04-23T14:30:11Z",
  "source_file": "data/closed-won/acme-closed-won-2026q1.csv",
  "file_size_bytes": 284712,
  "encoding": "utf-8",
  "has_bom": false,
  "row_count": 847,
  "column_count": 42,
  "severity": "warnings",
  "findings": [
    {
      "severity": "warning",
      "code": "duplicate_domains",
      "detail": "4.2% of rows have duplicate domains after normalization. 36 rows affected.",
      "affected_rows_sample": [17, 41, 82, 105, 149],
      "recommendation": "Consider deduping before running pattern-recognition, or confirm duplicates are intentional (e.g., multi-entity customers)."
    },
    {
      "severity": "warning",
      "code": "mixed_currency_format",
      "detail": "Column 'estimated_arr_usd' has mixed formats: '$2.4M', '2400000', '2,400,000'.",
      "recommendation": "Normalize to numeric. Suggested regex: strip `[$,]`, convert `M`/`K`/`B` suffixes to multipliers."
    },
    {
      "severity": "info",
      "code": "likely_unique_id_column",
      "detail": "Column 'crm_id' has cardinality = row_count (847). Not useful for pattern analysis.",
      "recommendation": "pattern-recognition will skip this column."
    },
    {
      "severity": "warning",
      "code": "pii_in_csv",
      "detail": "Columns 'primary_contact_email' and 'primary_contact_name' contain personal data.",
      "recommendation": "Confirm the file is sanitized before any git push. data/ is gitignored in this repo but not in forks."
    }
  ],
  "column_diagnosis": {
    "domain": {
      "type_declared": "string",
      "type_inferred": "string",
      "null_rate": 0.00,
      "cardinality": 811,
      "duplicate_rate": 0.042,
      "notes": "Normalize before use: 36 duplicate domains after lowercase + strip www."
    },
    "headcount": {
      "type_declared": "string",
      "type_inferred": "numeric (after coercion)",
      "null_rate": 0.03,
      "cardinality": 142,
      "coercion_losses": 8,
      "coercion_loss_samples": ["~200", "50-100", "unknown"],
      "notes": "Values like '~200' and '50-100' cannot be coerced to int. Consider cleaning."
    },
    "closed_won_date": {
      "type_declared": "string",
      "type_inferred": "date",
      "null_rate": 0.01,
      "cardinality": 284,
      "parse_failures": 3,
      "earliest_parsed": "2023-01-14",
      "latest_parsed": "2026-04-02",
      "notes": "3 rows have un-parseable dates — flagged for manual review."
    }
  },
  "recommended_next_action": "Fix the 2 warnings OR acknowledge them and proceed. pattern-recognition will run but will surface the warnings in its self-diagnostics."
}
```

For `severity: critical`, include:

```json
"critical_blockers": [
  "Duplicate-domain rate 34% exceeds 30% threshold. Dedupe before proceeding.",
  "Row 47 has 39 columns (expected 42). Likely malformed CSV — inspect."
],
"recommended_next_action": "Do NOT run pattern-recognition until the critical blockers above are resolved."
```

---

## When done

Print to user:

```
Data audit complete: data/closed-won/<file>.csv
  Severity: <clean | warnings | critical>
  Rows: <N>, Columns: <M>, Encoding: <enc>
  Findings: <crit> critical, <warn> warnings, <info> info
  <One-line per critical or warning finding>
Written to data/closed-won/.data-audit.json
<If critical:> ⚠️  pattern-recognition will refuse to run until blockers are resolved.
<If warnings:> ✓ You may proceed to pattern-recognition; warnings will surface in its self-diagnostics.
<If clean:> ✓ Clean. Proceed to pattern-recognition.
```

---

## Anti-patterns

- Do NOT modify the source CSV. This skill is read-only on the CSV.
- Do NOT run pattern-recognition from within this skill. The user (or the loop) decides.
- Do NOT silently lower severity. If a check produces a critical finding, it stays critical.
- Do NOT call external APIs.
