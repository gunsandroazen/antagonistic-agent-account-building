# Databar

## What it's good for
Credit-friendly enrichment + search. Growing competitor to Clay.

## Credentials
- Environment variable: `DATABAR_API_KEY`
- Obtain: https://databar.ai

## API / access method
- Endpoint: `https://api.databar.ai/v1/search/companies`
- Auth: Bearer token

## Filter schema
- `industry`, `headcount_range`, `country`, `state`, `technology`, `funding_total_usd`

## Translation from target-description.md
Straightforward — Databar's schema is close to how people describe firmographic signatures.

## Output schema
CSV with: `domain, name, headcount, hq, industry, technologies, funding_total, linkedin_url`.

## Rate limits
- 100 requests/minute.
- Per-result credit cost — check workspace balance before a big pull.

## Notes
Decent ecom coverage.
