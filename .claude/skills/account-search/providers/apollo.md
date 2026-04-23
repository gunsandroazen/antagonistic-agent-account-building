# Apollo

## What it's good for
Broad B2B coverage, strong on SaaS and tech. Good for mid-market firmographic search.

## Credentials
- Environment variable: `APOLLO_API_KEY`
- Obtain: https://app.apollo.io/#/settings/integrations/api

## API / access method
- Endpoint: `https://api.apollo.io/v1/mixed_companies/search`
- Auth: `X-API-Key` header

## Filter schema
See https://docs.apollo.io/reference/organization-search. Key filters:
- `organization_num_employees_ranges`: list of strings like `["50,100", "101,250"]`
- `organization_locations`: list of city/state/country
- `organization_industry_tag_ids`: list of Apollo industry tag IDs
- `revenue_range`: `{ "min": ..., "max": ... }`
- `currently_using_any_of_technology_uids`: list of Apollo tech UIDs
- `organization_latest_funding_stage_cd`: list of funding stages

## Translation from target-description.md
- Headcount bands → `organization_num_employees_ranges` (convert "50-500" → `["50,100","101,250","251,500"]`)
- HQ region → `organization_locations` (use full location strings)
- Tech stack mentions → `currently_using_any_of_technology_uids` (requires a lookup against Apollo's tech tag index; cache locally in `.claude/skills/account-search/providers/apollo-tech-uids.json` if needed)
- Funding stage → `organization_latest_funding_stage_cd`

## Output schema
CSV with: `domain, name, headcount, hq_city, hq_state, hq_country, industry, funding_stage, estimated_revenue, tech_stack` (comma-joined string).

## Rate limits
- 60 requests/minute, 10,000 records/day on Professional.
- Batch size: 200 per page.
- 429 → exponential backoff starting at 2s.

## Notes
Apollo's industry tag IDs and tech UIDs are opaque — the skill should maintain a local cache and refresh weekly.
