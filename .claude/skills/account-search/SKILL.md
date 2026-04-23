---
name: account-search
description: Use after data/target-description.md exists and the user wants to pull a wide raw account list from GTM databases (Apollo, Ocean, Clay, Databar, Exa, FullEnrich, Store Leads). Translates the target description into provider-specific search queries, runs them, writes raw results to data/accounts-raw/. Remix-able — users add their own provider adapters.
---

# Account Search Skill

## Your role

Turn `data/target-description.md` into wide queries against GTM databases. Pull raw accounts. Write the results to `data/accounts-raw/`. Do not score, filter, or tier — that's for account-scoring.

## Preconditions

1. `data/target-description.md` exists.
2. At least one provider under `.claude/skills/account-search/providers/*.md` (other than `README.md`) describes a provider the user has credentials for. Environment variables expected per provider are documented in each provider file.

## Provider registry

Read every `.md` file under `.claude/skills/account-search/providers/` (except `README.md`). Each one describes a single provider: what it's good for, its filter schema, how to translate target-description fields into its filters, its API endpoint or MCP server, and any rate-limit notes.

**This is the remix surface.** If the user has added their own `my-provider.md`, you pick it up automatically.

## How to query

1. Read `data/target-description.md`. Extract the firmographic signature and disqualifiers.
2. Check environment variables to decide which providers are configured. Skip providers without credentials.
3. For each configured provider:
   - Translate the firmographic signature into that provider's filter schema (the provider file tells you how).
   - Run the query.
   - Write results to `data/accounts-raw/{provider}-{YYYYMMDD-HHMMSS}.csv`.
4. After all providers run, write a manifest at `data/accounts-raw/manifest.json`:

```json
{
  "run_at": "2026-04-23T14:32:01Z",
  "target_description_source": "data/target-description.md",
  "providers_run": [
    {
      "provider": "apollo",
      "result_count": 47213,
      "filters_used": { "... provider-specific ..." },
      "output_file": "data/accounts-raw/apollo-20260423-143201.csv"
    }
  ],
  "total_unique_domains": 52817
}
```

5. Dedupe across providers **by domain** (canonical, lowercased, no www). The deduped master list goes into `data/accounts-raw/deduped-{YYYYMMDD-HHMMSS}.csv`.

## Wide, not narrow

Goal is tens of thousands to millions of rows. **If a query returns fewer than 500 results, relax filters and retry.** Note the relaxation in the manifest. Tight filters at search time defeat the purpose — scoring is where narrowing happens.

## Anti-patterns

- Do NOT score, tier, or filter results. Raw is the point.
- Do NOT enrich results beyond what providers return natively.
- Do NOT dedupe against the user's CRM — that's a separate step the user owns.
- Do NOT call `account-scoring` or write `scoring/*`.
- Do NOT invent providers not represented by a `.md` file in `providers/`.

## When done

Print: `"Pulled N unique accounts across M providers. Deduped master list: data/accounts-raw/deduped-{timestamp}.csv. Run account-scoring next."`
