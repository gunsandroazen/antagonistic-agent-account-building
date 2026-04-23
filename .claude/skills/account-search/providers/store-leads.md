# Store Leads

## What it's good for
Ecommerce-specific. Indexes Shopify, WooCommerce, BigCommerce, and other storefronts. If you sell to DTC brands, this is often the best single source.

## Credentials
- Environment variable: `STORE_LEADS_API_KEY`
- Obtain: https://storeleads.app

## API / access method
- Endpoint: `https://storeleads.app/json/api/v1/all/domains`
- Auth: Token in query string

## Filter schema
- `platform`: `"shopify" | "woocommerce" | "bigcommerce" | ...`
- `country_code`: ISO 3166-1 alpha-2
- `category`: product category (Store Leads has its own taxonomy)
- `employee_range`: bands
- `technologies`: list of tech slugs (e.g., `klaviyo`, `recharge`, `gorgias`)
- `estimated_monthly_sales_min/max`

## Translation from target-description.md
- "DTC / ecommerce" → platform filter
- Tech stack → `technologies`
- HQ country → `country_code`
- "Mature brand" / "early brand" → `estimated_monthly_sales` bands

## Output schema
CSV with: `domain, name, platform, country, category, estimated_monthly_sales, technologies, employee_count`.

## Rate limits
- 120 requests/minute.
- Result caps at 10,000 per query — paginate.

## Notes
Only useful if the ICP is ecom. Skip this provider for B2B SaaS.
