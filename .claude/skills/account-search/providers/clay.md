# Clay

## What it's good for
Orchestration layer on top of many providers. Good if you already have a Clay workspace with tables configured.

## Credentials
- Environment variable: `CLAY_API_KEY` + `CLAY_WORKSPACE_ID`
- Obtain: https://clay.com (paid plans only)

## API / access method
- Clay's API is webhook-driven. You POST a search spec, Clay runs it against whatever providers your workspace has connected, and returns results to a webhook URL.
- Endpoint: `https://api.clay.com/v1/sources/search`
- Auth: Bearer token

## Filter schema
Depends entirely on what sources the user's workspace has enabled. Most common:
- `company_name`, `domain`, `headcount`, `hq_country`, `industry`, `tech_used`

## Translation from target-description.md
Treat Clay as a meta-provider. The skill should write the query spec and let Clay fan out.

## Output schema
Varies by source. Clay normalizes basic firmographics; extra columns depend on which sources fired.

## Rate limits
Credit-based. The talk explicitly warns this is why iterating in Clay is expensive — use this skill's direct-provider paths for heavy iteration.

## Notes
If the user has Clay, they probably already have a workspace. Do not try to create tables programmatically.
