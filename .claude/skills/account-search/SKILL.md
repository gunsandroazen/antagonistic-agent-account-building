---
name: account-search
description: Use after data/target-description.md exists. Pulls a wide raw account list from GTM databases (Apollo, Ocean, Clay, Databar, Exa, FullEnrich, Store Leads, and any user-added providers) by translating the firmographic signature into provider-specific filters. Handles credential discovery, multi-provider fanout, pagination to exhaustion, canonical-domain dedup across providers, schema normalization into a common columns set, relaxation when queries return too few results, and rate-limit backoff. Writes per-provider CSVs, a deduped master list, a normalized master list, and a manifest with every filter and retry decision. Does not score, tier, or filter for fit — that is account-scoring's job.
---

# Account Search Skill

## Your role

Turn `data/target-description.md` into wide, exhaustive queries against every configured GTM provider. Pull every matching account. Normalize schemas. Dedup by canonical domain. Write artifacts so rich that `account-scoring` can run directly against the output without guessing.

You are a data-gathering machine, not a filter. Wide is the point. Narrowing happens at scoring.

---

## Preconditions

1. `data/target-description.md` exists and is non-empty.
2. At least one provider file exists under `.claude/skills/account-search/providers/` (other than `README.md`).
3. At least one provider's env vars are set. If zero providers have credentials, STOP with a message listing which env vars each provider needs.

---

## Tooling

- **HTTP:** Python `requests` (or `httpx` if available). If neither is installed, use stdlib `urllib.request` — but warn the user that retry/backoff becomes more primitive.
- **MCP providers:** if a provider file declares an `mcp__<name>__<tool>` call, prefer the MCP path over raw HTTP — it handles auth and pagination more cleanly.
- **CSV:** pandas preferred, stdlib `csv` as fallback.
- **Rate limiting:** respect the `Rate limits` section of each provider file. Implement exponential backoff on 429 (2s → 4s → 8s → 16s, max 5 retries) and on 5xx (1s → 2s → 4s, max 3 retries).
- **Concurrency:** run providers in parallel (one HTTP session per provider), but never parallelize requests to the same provider — that invites rate-limit cascades.

---

## Pipeline

### Stage 1 — Discover configured providers

1. Read every `.md` file in `.claude/skills/account-search/providers/` except `README.md`.
2. Parse the `## Credentials` section of each to extract the env var name(s) the provider requires.
3. Check `os.environ` for each. Build a list of providers where ALL required env vars are set.
4. If the list is empty, STOP with:
   ```
   No providers configured. Set at least one of:
     - APOLLO_API_KEY       (providers/apollo.md)
     - OCEAN_API_KEY        (providers/ocean.md)
     - CLAY_API_KEY + CLAY_WORKSPACE_ID  (providers/clay.md)
     - DATABAR_API_KEY      (providers/databar.md)
     - EXA_API_KEY          (providers/exa.md)
     - FULLENRICH_API_KEY   (providers/fullenrich.md)
     - STORE_LEADS_API_KEY  (providers/store-leads.md)
   Then re-run account-search.
   ```

### Stage 2 — Parse the target description

Read `data/target-description.md`. Extract structured content from these sections:
- **Firmographic signature** — bullets grouped by family (Location, Size, Maturity, Tech stack, Industry).
- **Disqualifiers** — bullets that define negative filters.
- **Confidence notes** — "Strong signal" items carry more weight in filter construction.

Build an internal `TargetSignature` dict:
```python
target_signature = {
  "location": {
    "countries": ["US"],              # ISO codes
    "regions": ["Northeast"],          # our region taxonomy
    "metros": ["NYC", "Boston"],       # metro codes where providers support them
    "states": ["NY", "NJ", "MA", "CT"]  # US state codes
  },
  "size": {
    "headcount_min": 50,
    "headcount_max": 300,
    "revenue_min_usd": 1000000,
    "revenue_max_usd": 50000000   # generous upper bound — wide is the point
  },
  "maturity": {
    "funding_stages": ["Seed", "Series A", "Series B", "Series C"],
    "ownership_types": ["Private"],
    "company_age_min_years": 2,
    "company_age_max_years": null
  },
  "tech_stack": {
    "required_any": ["Segment"],      # strong-signal tools
    "preferred": ["Snowflake", "dbt"] # soft-signal tools — don't hard-filter
  },
  "industry": {
    "include": ["SaaS", "MarTech", "Analytics", "Data Infrastructure", "Fintech"],
    "exclude": []
  },
  "disqualifiers": {
    "ownership_types": ["Public"],
    "countries_exclude": []           # non-US excluded unless explicitly listed as disqualifier
  }
}
```

**Only hard-filter on disqualifiers and strong-signal firmographics.** Soft signals become scoring weights later; filtering on them now narrows the funnel too early.

### Stage 3 — Per-provider query construction and execution

For each configured provider, in parallel:

1. Load the provider's `.md` file and follow its **Translation from target-description.md** section to map `target_signature` into the provider's filter schema.
2. Construct the query. Log the exact query in the manifest.
3. Execute with pagination to exhaustion, respecting rate limits. Each provider's `.md` file declares its max page size.
4. Write results as `data/accounts-raw/<provider>-<YYYYMMDD-HHMMSS>.csv` with whatever columns the provider returns natively.
5. Record in the manifest:
   - `query_sent`
   - `result_count`
   - `pages_fetched`
   - `time_elapsed_seconds`
   - `rate_limit_events` (count of 429s hit)
   - `retries`
   - `errors` (if any)

### Stage 4 — Relaxation on undersized results

If a provider returns < 500 results AND no errors, the filters are probably too tight. Relax in this order (stop on first threshold reached):

1. Drop the `tech_stack.required_any` filter — move it to "preferred."
2. Expand headcount bounds by ±50% (e.g., 50-300 → 25-450).
3. Expand funding stage set by one stage in each direction (Series A-C → Seed-D).
4. Drop industry filter (keep only country/region).
5. Keep ONLY country + disqualifiers.

Record every relaxation step in the manifest under `relaxation_trace`. If the final query still returns <500 AND the relaxation trace is exhausted, log an error and move on — but keep the results.

### Stage 5 — Schema normalization

Each provider returns a different CSV schema. Produce a **normalized master list** with this canonical column set:

```
domain,
company_name,
linkedin_url,
headcount,
hq_city,
hq_state_or_region,
hq_country,
industry,
funding_stage,
funding_total_usd,
estimated_revenue_usd,
tech_stack,              # comma-joined string
founded_year,
ownership_type,
source_providers         # comma-joined list of providers that returned this domain
```

Where a provider doesn't supply a column, leave it null. Each provider's `.md` file should document how its columns map to this canonical set; if a column isn't documented, make a best-effort mapping and note it in the manifest's `schema_mapping_notes`.

### Stage 6 — Dedup across providers

Compute canonical domain: lowercase, strip leading `www.`, strip trailing slash, strip query string. Group rows by canonical domain.

For domains that appear in multiple provider outputs, merge rows:
- Take the non-null value for each column from the first provider that has it, preferring providers in this order (by data quality): `ocean > apollo > fullenrich > databar > clay > store-leads > exa`. This order can be overridden in the provider file's `Notes` section if a provider should rank differently.
- `tech_stack` merges by union of all providers' tech lists.
- `source_providers` lists all providers that returned this domain.

Write the deduped normalized list to `data/accounts-raw/deduped-<YYYYMMDD-HHMMSS>.csv`.

### Stage 7 — Manifest

Write `data/accounts-raw/manifest.json`:

```json
{
  "generated_at": "2026-04-23T14:32:01Z",
  "target_description_source": "data/target-description.md",
  "target_signature_parsed": { "... full parsed dict ..." },
  "providers_configured": ["apollo", "ocean", "exa"],
  "providers_run": [
    {
      "provider": "apollo",
      "query_sent": { "... full filter payload ..." },
      "pages_fetched": 237,
      "result_count": 47213,
      "time_elapsed_seconds": 312.4,
      "rate_limit_events": 5,
      "retries": 2,
      "errors": [],
      "relaxation_trace": [],
      "output_file": "data/accounts-raw/apollo-20260423-143201.csv",
      "schema_mapping_notes": "Apollo 'organization_num_employees' → canonical 'headcount'"
    },
    {
      "provider": "ocean",
      "query_sent": { "seed_domains": "<42 Closed-Won domains>", "min_similarity": 0.6 },
      "pages_fetched": 8,
      "result_count": 6842,
      "time_elapsed_seconds": 94.1,
      "rate_limit_events": 0,
      "retries": 0,
      "errors": [],
      "relaxation_trace": ["dropped tech_stack.required_any because result_count=241 on first attempt"],
      "output_file": "data/accounts-raw/ocean-20260423-143201.csv"
    }
  ],
  "normalization": {
    "canonical_columns": ["domain", "company_name", "..."],
    "merged_file": "data/accounts-raw/deduped-20260423-143201.csv"
  },
  "dedup": {
    "raw_row_count": 54055,
    "unique_domain_count": 47891,
    "cross_provider_overlap": {
      "apollo_ocean": 4120,
      "apollo_fullenrich": 892,
      "ocean_fullenrich": 201
    }
  },
  "warnings": []
}
```

### Stage 8 — Ocean seed handling (special case)

If `ocean` is a configured provider, it needs Closed-Won domains as seeds (see `providers/ocean.md`). Read `data/closed-won/*.csv`, extract the `domain` column (or `website` if `domain` is absent — normalize), pass as seeds. Cap at 500 seeds (Ocean's typical limit); if more, sample randomly with seed=42 for reproducibility and note in the manifest.

---

## Wide, not narrow

Goal: tens of thousands to millions of rows across providers. Unless the user has an exotic ICP, hitting <5,000 across all providers is a signal that either (a) the target-description is too narrow, (b) the filter translation is over-constraining, or (c) the disqualifiers are too aggressive. The relaxation trace should catch this. If it doesn't, emit a prominent warning in the manifest.

---

## Anti-patterns

- Do NOT score, tier, or filter by fit. Raw is the point.
- Do NOT enrich results beyond what providers return natively. That is downstream's job.
- Do NOT dedupe against the user's CRM — that's the user's call.
- Do NOT call `account-scoring` or write `scoring/*`.
- Do NOT invent providers that lack a `.md` file in `providers/`.
- Do NOT persist API keys to disk. Read from env; use only in memory.
- Do NOT skip the manifest. The manifest IS the audit trail.

---

## When done

Print:

```
Account search complete.
  Providers run: <list>
  Raw rows: <total_raw>
  Unique domains: <unique>
  Cross-provider overlap: <X%>
  Relaxations applied: <list or "none">
  Warnings: <count>

Outputs:
  Per-provider CSVs: data/accounts-raw/<provider>-<timestamp>.csv
  Deduped normalized master: data/accounts-raw/deduped-<timestamp>.csv
  Manifest: data/accounts-raw/manifest.json

Next: `/skill account-scoring` (will run in generate mode first, then run mode after you hand-edit scoring/).
```
