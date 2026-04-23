# Exa

## What it's good for
Neural web search. Good for finding companies by description rather than structured filters — e.g., "companies that sell water filtration to dental clinics."

## Credentials
- Environment variable: `EXA_API_KEY`
- Obtain: https://exa.ai

## API / access method
- Endpoint: `https://api.exa.ai/search`
- Auth: Bearer token

## Filter schema
- `query`: natural language description
- `numResults`: up to 1000 per call
- `type`: `"neural"` or `"keyword"`
- `category`: `"company"`

## Translation from target-description.md
Use the one-sentence description and firmographic signature to compose a rich natural-language query. Exa is at its best when the query reads like a sentence a human would search.

## Output schema
CSV with: `url, title, snippet, score` — the skill must post-process to extract company domain and name.

## Rate limits
- 10 requests/second.
- Per-result cost.

## Notes
Exa returns URLs, not structured company records. You'll need to resolve to domains and may lose some results in post-processing.
