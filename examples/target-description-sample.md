# Best-Fit Customer

## One-sentence description
US-Northeast-based venture-backed B2B SaaS companies in the marketing-analytics-data stack, with 50-300 employees and modern data infrastructure (Segment + Snowflake + dbt).

## Firmographic signature
- **Headcount:** 50-300 (concentrated 85-250)
- **HQ region:** US Northeast — heavily NYC/Brooklyn, with Boston/Cambridge secondary
- **Ownership:** private (venture-backed)
- **Funding stage:** Series A through Series C (most density at Series B)
- **Industry vertical:** MarTech / Analytics / Data Infra / Fintech (the "modern data stack" orbit)
- **Tech stack signal:** Segment is present in ~85% of Closed-Won; Snowflake + dbt appear together in >60%
- **ARR band:** $1M-$4M estimated ARR

## Disqualifiers
- **Public companies.** Our Closed-Won is 100% private — public-company buying cycles differ fundamentally.
- **Non-US HQ.** We have never closed international; disqualify until we prove we can.
- **Pre-seed / bootstrap.** Companies without institutional funding lack the budget and urgency we see.
- **Headcount <30 or >500.** Too early or too mature.

## Confidence notes
- **Strong signal:** Headcount band, US Northeast HQ, Segment in tech stack. These survived all 3 rounds of the pattern-antagonist fight unchanged.
- **Soft signal:** Series B specifically (vs A or C) — may be selection bias from our own outbound patterns, not a customer feature. Flagged for review.
- **Known unknowns:** Industry classification is noisy — "MarTech" vs "Analytics" vs "Data Infra" often overlap for the same company. Don't over-filter on industry alone.

## Round log
| Round | Candidates | Kept | Killed | Notable changes |
|-------|-----------|------|--------|-----------------|
| 1 | 94 | 11 | 83 | Kept: headcount band, HQ region, ownership, funding stage, tech stack signals, ARR band. Killed: domain TLD patterns, specific city granularity, founding year. |
| 2 | 98 | 14 | 84 | Resurrected "Segment in tech stack" after antagonist initially killed as "too specific" — on re-argument, 85% match rate vs. ~25% market baseline passed the base-rate test. Added interaction pattern "Segment + Snowflake + dbt together." |
| 3 | 98 | 14 | 84 | Converged (0 state changes). |

**Killed patterns worth reviewing manually:**
- `funding_under_10m`: 60% match rate — antagonist killed for actionability (hard to filter on total funding precisely). Worth revisiting if your provider supports it.
- `hq_brooklyn_specific`: real signal but rolled up into `hq_northeast`. If you're doing hyper-local ABM, restore.
