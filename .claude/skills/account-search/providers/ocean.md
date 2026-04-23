# Ocean.io

## What it's good for
Lookalike-based search — feed in Closed-Won domains, get statistically similar companies. Stronger than filter-based search for "more of these."

## Credentials
- Environment variable: `OCEAN_API_KEY`
- Obtain: https://ocean.io (contact sales)

## API / access method
- Endpoint: `https://api.ocean.io/v2/lookalikes`
- Auth: Bearer token

## Filter schema
- `seed_domains`: list of Closed-Won domains (required)
- `min_similarity`: float 0-1 (recommend 0.6)
- `filters`: optional hard filters (country, headcount bands) layered on top of lookalike scores

## Translation from target-description.md
- Feed the Closed-Won domains as seeds (skill reads from `data/closed-won/*.csv` to extract seed domains).
- Use firmographic signature ONLY as hard filters, not for search — let the lookalike model do its job.

## Output schema
CSV with: `domain, name, similarity_score, matched_seeds, headcount, hq_country, industry`.

## Rate limits
- 10 requests/minute typical.
- Lookalike queries are slow (5-30s). Budget accordingly.

## Notes
Ocean's strength is the model. Don't over-constrain with filters — trust the similarity score.
