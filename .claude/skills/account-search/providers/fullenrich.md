# FullEnrich

## What it's good for
Enrichment-first provider; its search is lighter than Apollo but the data quality is high once you have a list.

## Credentials
- Environment variable: `FULLENRICH_API_KEY`
- Obtain: https://fullenrich.com

## API / access method
- Endpoint: `https://api.fullenrich.com/v1/companies/search`
- Auth: Bearer token

## Filter schema
- `headcount_range`, `country`, `industry`, `domain` (for enrichment of known lists)

## Translation from target-description.md
Basic firmographic mapping. Best used AFTER another provider (Apollo, Ocean) returns a raw list — feed FullEnrich the domains for enrichment.

## Output schema
CSV with: `domain, name, headcount, hq, industry, revenue_estimate, employee_emails_available`.

## Rate limits
- 60 requests/minute.
- Credit-based.

## Notes
Complements other providers; rarely the sole source.
