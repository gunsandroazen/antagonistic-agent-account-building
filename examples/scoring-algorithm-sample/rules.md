# LLM-assisted scoring rules

These rules require classification or web research that deterministic code can't do reliably. The run-mode engine calls these out to a model, caching results by domain.

## rule: sells_to_data_teams

Use when we need to classify whether the company's primary buyer is a data/analytics/engineering team (vs. marketing, sales, or ops). Look at the company's homepage, customer logos, and any recent case studies. Return boolean.

## rule: modern_brand_positioning

Does the company position itself as modern / developer-friendly / AI-native in current marketing (homepage, recent blog posts)? Return boolean. This is soft signal — it correlates with fit but isn't deterministic.

## rule: likely_in_buying_window

Based on recent public signals (funding news within 6 months, new exec hires in data/analytics/RevOps roles, tech stack expansion), is this company likely in a buying window for our product? Use your judgment — return `"active" | "cooling" | "unknown"`.
