# Account Search Providers

One markdown file per provider. The `account-search` skill reads all files in this directory (except this README) and uses them to query GTM databases.

## Adding a new provider

Create `my-provider.md` with this structure:

```markdown
# <Provider Name>

## What it's good for
One or two sentences on which verticals / company types this provider indexes well.

## Credentials
- Environment variable(s) required: `MY_PROVIDER_API_KEY`
- How to obtain: <link or one-liner>

## API / access method
- Endpoint: `https://api.my-provider.com/v1/...`
- Or MCP server: `mcp__my_provider__search`
- Auth: Bearer token in `Authorization` header

## Filter schema
List the filters the provider accepts. Example:
- `industry`: string, one of [SaaS, Fintech, ...]
- `headcount_min`: int
- `headcount_max`: int
- `country`: ISO 3166-1 alpha-2
- `funding_stage`: one of [Seed, Series A, ...]

## Translation from target-description.md
Explain how to map the firmographic signature blocks in `data/target-description.md` to this provider's filters. Be specific:
- "Headcount: 50-500" → `{ "headcount_min": 50, "headcount_max": 500 }`
- "HQ: US Northeast" → `{ "country": "US", "region": ["NY", "MA", "CT", "NJ", "PA"] }`

## Output schema
Which columns the provider returns in its CSV export. Flag which ones map to standard columns (domain, company name, headcount, HQ, funding).

## Rate limits
Per-minute / per-day limits. Recommended batch size. Retry strategy on 429.

## Notes
Anything else — quirks, known-bad filters, special behavior.
```

## Provider files in this directory

- `apollo.md` — Apollo.io
- `ocean.md` — Ocean.io
- `clay.md` — Clay (via workspace + webhook)
- `databar.md` — Databar
- `exa.md` — Exa (Exa.ai)
- `fullenrich.md` — FullEnrich
- `store-leads.md` — Store Leads (ecom-specific)
