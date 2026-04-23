---
name: business-context
description: Run FIRST before any other skill in this repo. Produces data/business-context.md — the user's own description of their business, customers, goals, constraints, and confounders, written in their own words. This document is the ground truth the antagonist uses to judge pattern relevance. Runs interactively when the user is available (asks targeted questions one at a time, builds context in passes); runs from a brief when the user has pre-written notes or a marketing site; runs in minimal mode when the user explicitly wants to start fast. Industry-agnostic — works for any business analyzing any tabular data for any decision. Re-invoke any time the business evolves or a new decision is in scope.
---

# Business Context Skill

## Your role

Produce `data/business-context.md` — a structured document describing the user's business, what they sell, who they sell to, what decision they're trying to inform with pattern discovery, what "actionable" means for their stack, and what data-collection confounders might apply.

This document is the **basis of relevance** for everything downstream. The pattern-recognition skill stays deliberately ignorant of it (universal pattern discovery should not be biased by what the user hopes to find). The antagonist uses it to prosecute relevance. The loop uses it to shape the target-description artifact. The scoring skill uses it to calibrate rules.

You are industry-agnostic. The user could be selling software, consulting, lumber, legal services, physical products, insurance, anything. The questions you ask adapt to their business, not the other way around.

---

## Invocation modes

Detect mode based on what the user provides:

### Mode A — Interactive (preferred)

Default when the user invokes `/skill business-context` without arguments. Ask questions one at a time, accumulating answers. DO NOT ask all questions at once — that's overwhelming and produces shallow answers. One question, wait for reply, follow up if needed, then move on.

### Mode B — Brief ingestion

If the user provides a path to an existing document (marketing site export, deck, README, sales playbook, onboarding doc), ingest it and draft the context document. Then show the draft to the user and ask "anything missing or wrong?" before finalizing.

### Mode C — Minimal / fast-start

If the user says "minimal" or "just the essentials" or "I'll fill it in later," write a stub with only the three required sections filled from whatever they've said in conversation. Mark the rest as `_TBD — fill in before running antagonist_`.

### Mode D — Update existing

If `data/business-context.md` already exists, offer to either:
- **Review and edit** — walk through each section, confirming or updating.
- **Append addendum** — add a dated addendum at the bottom (useful when a new decision is in scope without invalidating the rest).
- **Replace** — start fresh (requires explicit confirmation).

---

## The questions (Interactive mode)

Ask these in order. Skip ones the user has already answered in conversation. Follow up when an answer is vague. Do not accept answers like "I don't know" without probing — the point is to produce something sharp.

### Section 1 — The business (REQUIRED)

**Q1.** In one or two sentences, what does your business do? Whose money are you trying to make?

**Q2.** How old is the business? How big? Rough revenue band or employee count is enough — if you don't want to share, skip.

**Q3.** What's the one thing your best customers do that your worst customers don't? (Open-ended — the answer might be operational, behavioral, firmographic, anything.)

### Section 2 — The customer (REQUIRED)

**Q4.** Describe your best-fit customer in your own words. Not jargon, not ICP-speak. The kind of description you'd give a new employee. Two or three sentences.

**Q5.** Is your customer a company, a specific role inside a company, an individual consumer, a household, a government entity, something else? (Affects whether downstream filters are firmographic, demographic, geographic, etc.)

**Q6.** Do you sell one offering or multiple? If multiple, do different offerings have meaningfully different customers? (Determines whether we should run the pattern loop per-segment.)

**Q7.** Name 3-5 specific customers who are exemplars of best-fit. (The antagonist uses these later to sanity-check whether the scoring algorithm tiers them correctly.)

**Q8.** Name 2-3 customers that were misfits — closed but turned out not to be a great match, churned, hated the product, anything. (Equally informative; "patterns to avoid" is often sharper than "patterns to seek.")

### Section 3 — The decision (REQUIRED)

**Q9.** What decision will this analysis inform? Examples the skill will recognize:
- Building a target account list for outbound GTM
- Prioritizing inbound leads
- Designing an ICP filter for paid ads
- Segmenting an existing book of business
- Understanding churn
- Something else — describe it
- (If the user says something not on the list, capture it verbatim.)

**Q10.** What does "actionable" mean for you? What tools will the output flow into? Examples: Apollo/Salesforce/HubSpot filters; ad platform audiences; CRM tiering; SDR call lists; manual review. The answer here shapes the antagonist's Actionability test.

**Q11.** What's your time horizon for acting on this? This quarter? This year? Ongoing?

### Section 4 — Data and confounders (IMPORTANT)

**Q12.** What data are you analyzing? Describe the CSV(s) you plan to run through pattern-recognition. Where did the data come from? Closed-Won from CRM? Survey responses? Transaction logs? A scraped list?

**Q13.** Over what period? How was it collected?

**Q14.** If the data is about customers (Closed-Won, active users, etc.), was there anything *selective* about how those customers reached you? Examples:
- Heavy outbound to a specific geography → geographic bias.
- Warm-intro network → investor/alumni bias.
- Partner referrals → partner's ecosystem bias.
- Pricing gate (you didn't sell below $X) → revenue-floor bias.
- Channel concentration (mostly inbound from one content piece) → topical bias.

**Be specific about what you know.** The antagonist uses this to prosecute patterns that look more like collection artifacts than customer features.

**Q15.** Are there dimensions you KNOW matter but the data probably doesn't capture well? (e.g., "I know buyer persona matters but our CRM doesn't tag it.") These become Known Unknowns in the final target description.

### Section 5 — Constraints and disqualifiers (IMPORTANT)

**Q16.** Hard disqualifiers — who are you definitely NOT going after, no matter what the data says? Examples: a specific competitor segment, regulated industries, geographies, company sizes. These become negative-weight rules.

**Q17.** Soft preferences — who do you *prefer* to target but aren't ruling out? (Goes into scoring weights, not filters.)

**Q18.** Any legal / compliance / brand constraints on who you can sell to? (GDPR, HIPAA, industry-specific rules, exclusivity agreements.)

### Section 6 — Taste and judgment (OPTIONAL but useful)

**Q19.** When you look at the patterns the tool surfaces, what kinds of patterns will you want to see more of? Less of? Helps the antagonist calibrate when the baseline data is ambiguous.

**Q20.** Is there anyone on the team who thinks about your customer differently than you do? Would they write a different version of this document? (If yes, consider having them also write one; the antagonist can compare.)

---

## Output: `data/business-context.md`

Synthesize answers into this exact structure. Every section is required even if thin. If a section is thin, say so explicitly — don't pad.

```markdown
# Business Context

_Generated: <ISO-8601 timestamp>_
_Mode: <interactive | brief | minimal | update>_
_Source: <conversation | path to brief | prior-version+update>_

---

## The business

<Q1-Q3 synthesized. 3-6 sentences. Plain language.>

**Operating signal:** <Q3 distilled into one sentence — the thing that separates best from worst customers in the user's own framing.>

---

## The customer

<Q4 verbatim or lightly edited.>

**Customer entity type:** <company | role-within-company | consumer | household | government | other — from Q5>
**Offering structure:** <single offering | N offerings with distinct customers | N offerings with overlapping customers — from Q6>

**Best-fit exemplars (from Q7):**
- <name>
- <name>
- <name>

**Misfit examples (from Q8):**
- <name> — <why>
- <name> — <why>

---

## The decision

**What this analysis will inform:** <Q9 — named decision>
**Downstream tools / actionability:** <Q10 — concrete tool list>
**Time horizon:** <Q11>

---

## The data

**Source CSV(s):** <Q12 — path(s) and origin>
**Collection period:** <Q13>
**How it was collected:** <Q13 continued — method>

**Known confounders (selection biases):**
- <Q14 item 1>
- <Q14 item 2>
- ...
- If none: "_User believes data collection was representative. Antagonist should still apply confound test conservatively._"

**Known unknowns (dimensions likely missing from the data):**
- <Q15 item 1>
- ...

---

## Constraints

**Hard disqualifiers (Q16):**
- <disqualifier 1> — <reason>
- ...

**Soft preferences (Q17):**
- <preference 1>
- ...

**Legal / compliance / brand constraints (Q18):**
- <constraint 1>
- ... or "None identified."

---

## Judgment

**Patterns the user wants to see more of (Q19):**
- ...

**Patterns the user wants to see less of (Q19):**
- ...

**Alternate perspectives within the team (Q20):**
- ... or "None identified — single-voice document."

---

## Downstream instructions for the antagonist

Based on the above, the antagonist should:

1. **For the Decision test**, accept as "concrete decisions" the following forms:
   - <derived from Q9 — e.g., "Filter changes in Apollo / Ocean" or "Scoring weight changes" or "Channel-strategy changes">

2. **For the Actionability test**, treat as "actionable at downstream tool":
   - <derived from Q10 — e.g., "Any filter supported by Apollo, Salesforce, or Meta Ads audience builder">

3. **For the Confound test**, treat these as plausible biases requiring extra scrutiny:
   - <derived from Q14 — user's own list>

4. **For the Base-rate test**, the reference population is:
   - <derived — e.g., "B2B SaaS venture-backed companies in the US" → use baselines' `_venture_backed_only` variants; or "US small businesses with >$1M revenue"; or "Consumers in the US aged 25-54"; or "custom population described in data/baselines.json">

5. **Disqualifier patterns to especially validate:**
   - <derived from Q16 — the user-declared disqualifiers; antagonist should keep these as disqualifier survivors even if the data alone wouldn't support them>

---

## For the loop / target-description

When the pattern-antagonist-loop synthesizes `data/target-description.md`, it should:
- Frame the best-fit customer description in the user's own voice from Q4.
- Respect the customer-entity-type from Q5 (if household/consumer, don't emit firmographic-only signatures).
- Carry forward the hard disqualifiers from Q16 whether or not the data surfaced them.
- Flag Known Unknowns from Q15 in the Confidence Notes section.

---

## For scoring

When the account-scoring skill runs:
- Downstream filters / rules should only reference dimensions that are **actionable per Q10**.
- Hard disqualifiers from Q16 become negative-weight rules regardless of lift.
- Best-fit exemplars from Q7 are added to `scoring/weights.yaml → tiers.t1.named_accounts_file` as a sense-check set — if they don't land in T1, the algorithm is broken.
```

---

## Execution rules

### When to probe

If the user's answer is:
- **One word** — ask a follow-up: "Can you say more?"
- **Jargon** — ask: "In plain language, what does that mean?"
- **Contradictory with an earlier answer** — call it out: "You said X earlier; now Y — which is it, or do both apply?"
- **Empty / "I don't know"** — offer an example and ask if that example matches their situation.

### When to stop asking

After each section, confirm: "Ready to move on to [next section]?" Users get tired fast; quality of answers decays. Better to have a sharp document for 3 sections than a mushy one for 6.

### When to infer vs ask

Basic demographic inferences (e.g., "if they mention Closed-Won, they have a sales org, so they're probably B2B") are fine. Customer-defining inferences are not — always confirm.

### Handling user resistance to specific questions

Some users won't want to name customers (Q7/Q8). That's fine — accept "N/A" and note in the document that exemplars weren't provided. The downstream sense-check will be weaker but the pipeline still works.

Some users won't want to share legal constraints (Q18). Accept "see fork-level private notes" and move on.

### Length target

The final `business-context.md` should be **400-1200 words**. Below 400 = too thin for the antagonist to use. Above 1200 = padding — tighten.

---

## Preconditions

1. The user is the person answering — or explicitly acting on behalf of the person who has the answers. If the user says "I don't know these answers, find someone who does," STOP and tell them to come back with the right person.
2. `data/` directory exists (created by the repo structure).
3. If `data/business-context.md` already exists, enter Mode D (update).

---

## Anti-patterns

- Do NOT assume the business is B2B SaaS. The repo is GTM-flavored because of the original talk, but forkers may be consultants, lawyers, physical-goods sellers, agencies, schools, governments, anything.
- Do NOT prescribe answers. Questions are open; user fills them.
- Do NOT ingest the user's marketing copy and parrot it back. Marketing copy describes who the business *says* they target; this document must describe who they *actually* close. Probe for the gap.
- Do NOT sanitize or generalize the user's language. The document reads in their voice because that's what makes the antagonist's relevance judgment sharper.
- Do NOT run other skills from within this one. Produce the artifact; the user (or the loop) runs the next step.
- Do NOT invent confounders. If the user says "collection was clean" and can articulate why, accept it.

---

## When done

Print to user:

```
Business context captured.
  Mode: <interactive | brief | minimal | update>
  Sections filled: <N of 6>  (required: 1-3 / important: 4-5 / optional: 6)
  Length: <word_count> words
  Best-fit exemplars provided: <N>  (used later for scoring sense-check)
  Known confounders identified: <N>
  Hard disqualifiers: <N>

Written to data/business-context.md.

Next steps:
  1. Put your CSV in data/closed-won/ (or wherever — pattern-recognition accepts any path)
  2. Run /skill data-audit on the CSV
  3. Run /skill pattern-antagonist-loop — the loop reads business-context.md automatically

Re-invoke /skill business-context any time:
  - The business evolves (new offering, new segment, pivot)
  - A new decision is in scope
  - The data source changes
```
