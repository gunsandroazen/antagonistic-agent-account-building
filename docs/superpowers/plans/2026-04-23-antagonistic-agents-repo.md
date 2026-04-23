# Antagonistic Agents Repo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a public, fork-and-run Claude Code skills repo that lets GTM operators run the 7-step "antagonistic agents in account building" pipeline from Elliot Roazen's NYC GTM 2026 talk.

**Architecture:** Five Claude Code skills (`pattern-recognition`, `antagonist`, `pattern-antagonist-loop`, `account-search`, `account-scoring`) that read/write against known paths under `data/` and `scoring/`. The orchestrator skill runs the pattern↔antagonist fight up to 3 rounds and emits a target-description markdown artifact. The scoring skill is two-mode (generate / run) with a mandatory Closed-Won sense-check gate. Provider adapters for `account-search` live as one markdown file per provider so users can drop in their own without editing the skill.

**Tech Stack:** Claude Code skills (SKILL.md with YAML frontmatter + markdown body). No runtime dependencies at clone time. Skill bodies may invoke Bash, Python, or other tools the user already has. Repo is version-controlled with git, hosted on GitHub at `gunsandroazen/antagonistic-agent-account-building`.

**Spec:** `docs/superpowers/specs/2026-04-23-antagonistic-agents-repo-design.md`

**Notes for the implementer:**
- You have zero context for Claude Code skills. Read: `https://docs.claude.com/en/docs/claude-code/skills` before Task 1.
- A Claude Code skill is a file at `.claude/skills/<name>/SKILL.md` with YAML frontmatter (`name`, `description`) and a markdown body. Claude reads the description to decide when to invoke, then reads the body as instructions.
- There is no "test suite" in the traditional sense. Validation is: (a) YAML frontmatter parses, (b) the skill produces the expected output file when invoked against fixture data, (c) the sample `closed-won-sample.csv` produces a sensible `target-description.md`.
- Commit after every task. Keep commits small and descriptive.

---

## Task 0: Pre-flight

**Files:**
- Read: `docs/superpowers/specs/2026-04-23-antagonistic-agents-repo-design.md` (the spec)
- Verify: `README.md`, `LICENSE`, `.gitignore` already exist in repo root

- [ ] **Step 1: Read the spec end-to-end**

Open `docs/superpowers/specs/2026-04-23-antagonistic-agents-repo-design.md` and read it. This plan assumes you know the full spec.

- [ ] **Step 2: Verify starting state**

Run:
```bash
ls -la /Users/elliotroazen/claude-projects/antagonistic-agent-account-building/
git log --oneline
```
Expected: `README.md`, `LICENSE`, `.gitignore`, `docs/` present. Two commits on main (`Initial commit`, `Add design spec...`).

- [ ] **Step 3: Read Claude Code skills docs**

Open `https://docs.claude.com/en/docs/claude-code/skills` in a browser (or use WebFetch). Confirm you understand: frontmatter fields, `description` as a trigger, body as instructions, skills living at `.claude/skills/<name>/SKILL.md`.

---

## Task 1: Update `.gitignore` and scaffold `data/` + `scoring/`

**Files:**
- Modify: `.gitignore`
- Create: `data/closed-won/.gitkeep`
- Create: `data/patterns/.gitkeep`
- Create: `data/accounts-raw/.gitkeep`
- Create: `data/accounts-scored/.gitkeep`
- Create: `scoring/.gitkeep`

- [ ] **Step 1: Read current `.gitignore`**

Read `.gitignore` and note its current contents.

- [ ] **Step 2: Append data/scoring rules to `.gitignore`**

Append to `.gitignore`:
```
# User data — never commit real Closed-Won or account lists
data/**
!data/**/.gitkeep

# User-generated scoring algorithm — user forks commit these to their own fork,
# but the upstream template repo ships with scoring/ empty
scoring/**
!scoring/.gitkeep
```

- [ ] **Step 3: Create `.gitkeep` files**

Run:
```bash
mkdir -p data/closed-won data/patterns data/accounts-raw data/accounts-scored scoring
touch data/closed-won/.gitkeep data/patterns/.gitkeep data/accounts-raw/.gitkeep data/accounts-scored/.gitkeep scoring/.gitkeep
```

- [ ] **Step 4: Verify `.gitignore` works**

Run:
```bash
echo "test" > data/closed-won/scratch.csv
git status --short
```
Expected: `scratch.csv` does NOT appear in git status. Clean up: `rm data/closed-won/scratch.csv`.

- [ ] **Step 5: Commit**

```bash
git add .gitignore data/closed-won/.gitkeep data/patterns/.gitkeep data/accounts-raw/.gitkeep data/accounts-scored/.gitkeep scoring/.gitkeep
git commit -m "Scaffold data/ and scoring/ directories with gitignore rules"
```

---

## Task 2: Skill — `pattern-recognition`

**Files:**
- Create: `.claude/skills/pattern-recognition/SKILL.md`

- [ ] **Step 1: Create directory**

Run: `mkdir -p .claude/skills/pattern-recognition`

- [ ] **Step 2: Write `SKILL.md`**

Create `.claude/skills/pattern-recognition/SKILL.md` with this exact content:

````markdown
---
name: pattern-recognition
description: Use when the user has an enriched Closed-Won CSV in data/closed-won/ and wants to surface candidate patterns (location, headcount, ownership, funding, tech stack, HQ, etc.) that might define their best-fit customer. Outputs candidate patterns as JSON to data/patterns/candidates.json. Does NOT decide which patterns matter — that's the antagonist's job.
---

# Pattern Recognition Skill

## Your role

Surface every candidate pattern in the Closed-Won CSV. Be noisy. Overproduction is expected here — the antagonist skill will cut it down.

## Preconditions

1. Read `data/closed-won/`. It must contain **exactly one** `.csv` file. If zero or multiple, STOP and tell the user which state they're in.
2. Read the CSV header and a sample of rows. The file must have ≥20 rows and ≥5 columns. If not, STOP and tell the user the CSV is too small.

## How to analyze

For every column:
- Compute cardinality (distinct values), null rate, and top-10 values by frequency.
- For numeric columns, compute min/max/median and suggest natural bands (quartiles, or semantically meaningful bands like "headcount 1-10, 11-50, 51-200, ...").
- For text-heavy columns (descriptions, notes, free-text), extract recurring themes (use your own judgment; don't call external APIs).

Then surface interaction effects where obvious — e.g., `hq_city=NYC ∧ funding_stage=Series B` showing up more than either alone would predict.

**Bias toward breadth.** Surface dozens of patterns, even hundreds if the data supports it. Do not skip a column because it "looks low-signal." The antagonist decides what matters.

## Output contract

Write `data/patterns/candidates.json` with this structure:

```json
{
  "source_file": "data/closed-won/<filename>.csv",
  "row_count": 847,
  "column_count": 42,
  "patterns": [
    {
      "id": "hq_nyc",
      "dimension": "hq_city",
      "claim": "63% of Closed-Won are HQ'd in NYC",
      "evidence": {
        "match_rate": 0.63,
        "sample_matches": ["Acme Corp", "Beta Inc", "Gamma LLC"],
        "total_matches": 534
      },
      "hypothesis": "NYC proximity may correlate with fit — possibly sales-team geography, possibly real signal"
    }
  ]
}
```

Every pattern MUST have: `id` (slug), `dimension` (source column or interaction), `claim` (one sentence), `evidence` (quantitative), `hypothesis` (what it might mean — this is genuinely a guess, label it as such).

## Anti-patterns

- Do NOT rank, score, or filter patterns. That's the antagonist's job.
- Do NOT write `data/target-description.md`. That's the loop's job.
- Do NOT edit anything in `scoring/`. That's the account-scoring skill's job.
- Do NOT skip columns because you think they won't matter.
- Do NOT say "more analysis needed" — surface what you find, let the antagonist argue.

## When done

Print a one-line summary to the user: `"Surfaced N candidate patterns across M dimensions. Written to data/patterns/candidates.json. Run antagonist next (or pattern-antagonist-loop for the full fight)."`
````

- [ ] **Step 3: Validate YAML frontmatter parses**

Run:
```bash
python3 -c "
import re, yaml
with open('.claude/skills/pattern-recognition/SKILL.md') as f:
    content = f.read()
m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
fm = yaml.safe_load(m.group(1))
assert 'name' in fm and 'description' in fm
assert fm['name'] == 'pattern-recognition'
print('OK')
"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/pattern-recognition/SKILL.md
git commit -m "Add pattern-recognition skill"
```

---

## Task 3: Skill — `antagonist`

**Files:**
- Create: `.claude/skills/antagonist/SKILL.md`

- [ ] **Step 1: Create directory**

Run: `mkdir -p .claude/skills/antagonist`

- [ ] **Step 2: Write `SKILL.md`**

Create `.claude/skills/antagonist/SKILL.md` with this exact content:

````markdown
---
name: antagonist
description: Use after pattern-recognition to scrutinize every pattern in data/patterns/candidates.json and argue it down to what actually matters. Fights AI's two flaws — agreeable and overproduces. Outputs surviving patterns to data/patterns/survivors.json with explicit kill reasoning for rejects. Adversarial by design — default posture is skepticism.
---

# Antagonist Skill

## Your role

You are adversarial. Your default is to **kill** every pattern. A pattern survives only if it passes every test below. You are fighting two flaws that plague AI outputs: agreeableness and overproduction. Be willing to say "this is noise." Be terse. Do not hedge.

If you cannot write a one-sentence reason this pattern would change a GTM decision, **kill it**.

## Preconditions

`data/patterns/candidates.json` exists. If not, STOP and tell the user to run pattern-recognition first (or pattern-antagonist-loop).

## The four tests

For every pattern in `candidates.json`, answer all four. If any answer is "no" or "can't tell," **kill**.

1. **Decision test** — Would acting on this pattern change who we target or how we approach them? If not, kill.
2. **Base-rate test** — Is the claimed match rate meaningfully above the baseline for that dimension? "60% of customers are SaaS" means nothing if 60% of all B2B companies are SaaS. If the match rate is not clearly above the population baseline, kill.
3. **Coincidence test** — Is this pattern an artifact of how we've historically sold (sales team geography, warm intro network, outbound targeting) rather than a feature of good-fit customers? If likely an artifact, kill.
4. **Actionability test** — Can a real GTM database (Apollo, Ocean, Clay, Databar) actually filter on this? If not filterable, kill.

## Output contract

Write `data/patterns/survivors.json`:

```json
{
  "source_file": "data/patterns/candidates.json",
  "total_evaluated": 127,
  "survivors": [
    {
      "id": "...",
      "verdict": "kept",
      "reasoning": "One sentence on why each of the four tests passed.",
      "decision_impact": "Concrete change to GTM targeting/approach this pattern enables."
    }
  ],
  "killed": [
    {
      "id": "...",
      "verdict": "killed",
      "reason": "Which test failed and why. One sentence."
    }
  ],
  "summary": "X kept of Y. Dimensions that survived: <list>. Most-common kill reason: <reason>."
}
```

## Posture

- Every pattern is `kept` or `killed`. **No maybes, no "could be relevant," no "worth investigating."**
- Do NOT add new patterns — that's pattern-recognition's job.
- Do NOT soften verdicts because it "feels harsh." That's the whole point.
- Terse reasoning. One sentence per verdict.

## When done

Print to the user: `"Killed N of M patterns. Survivors written to data/patterns/survivors.json. Most survivors in dimension: <dimension>."`
````

- [ ] **Step 3: Validate frontmatter**

Run:
```bash
python3 -c "
import re, yaml
with open('.claude/skills/antagonist/SKILL.md') as f:
    content = f.read()
m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
fm = yaml.safe_load(m.group(1))
assert fm['name'] == 'antagonist'
print('OK')
"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/antagonist/SKILL.md
git commit -m "Add antagonist skill with kill-by-default posture"
```

---

## Task 4: Skill — `pattern-antagonist-loop`

**Files:**
- Create: `.claude/skills/pattern-antagonist-loop/SKILL.md`

- [ ] **Step 1: Create directory**

Run: `mkdir -p .claude/skills/pattern-antagonist-loop`

- [ ] **Step 2: Write `SKILL.md`**

Create `.claude/skills/pattern-antagonist-loop/SKILL.md` with this exact content:

````markdown
---
name: pattern-antagonist-loop
description: Use after the user has an enriched Closed-Won CSV in data/closed-won/ and wants the full pattern↔antagonist fight run end-to-end. Runs pattern-recognition, then antagonist, then up to 2 more rounds where the pattern agent may defend killed patterns and surface new ones, and the antagonist re-prosecutes. Outputs the surviving pattern set and writes data/target-description.md — the artifact describing the best-fit customer and why.
---

# Pattern-Antagonist Loop Skill

## Your role

Orchestrate the fight between pattern-recognition and antagonist. Run up to 3 rounds, stop early on convergence, then synthesize the surviving patterns into a human-readable target-customer description.

## Preconditions

`data/closed-won/` contains exactly one `.csv` file with ≥20 rows and ≥5 columns. If not, STOP with a clear error.

## Loop mechanics

### Round 1
1. Run the `pattern-recognition` skill. Output: `data/patterns/candidates-r1.json`.
2. Run the `antagonist` skill against it. Output: `data/patterns/survivors-r1.json`.

### Round 2 (grudge round)
1. Re-run `pattern-recognition`, but pass it a "grudge prompt" that includes the contents of `survivors-r1.json`. Instruct it to:
   - Pick the 3 killed patterns it most disagrees with and defend them with new evidence (different angle, interaction effect, adjacent dimension).
   - Surface interaction effects it missed in round 1 (e.g., NYC + Series B + fintech together beat any alone).
2. Output: `data/patterns/candidates-r2.json` (contains the defenses plus any new interaction patterns).
3. Re-run `antagonist`. Output: `data/patterns/survivors-r2.json`.

### Round 3 (final grudge round)
Same structure as Round 2. Outputs: `candidates-r3.json`, `survivors-r3.json`.

### Convergence rule
After round 2 or 3 finishes, compare `survivors-rN.json` to `survivors-r(N-1).json`. If fewer than 2 patterns changed state (kept→killed or killed→kept), STOP. Use the latest survivors file as final.

### Hard cap
**Maximum 3 rounds.** Never more. If the user wants more, they re-invoke this skill manually.

## Writing `data/target-description.md`

After the loop converges, synthesize the final survivors into this exact structure:

```markdown
# Best-Fit Customer

## One-sentence description
[Single sentence. Who they are, what they do, why they fit.]

## Firmographic signature
- [Pattern 1 — e.g., "Headcount: 50-500"]
- [Pattern 2 — e.g., "HQ: US Northeast, concentrated in NYC/Boston"]
- [Pattern N...]

## Disqualifiers
Patterns that explicitly kill fit when present:
- [e.g., "Public company — private-only in our Closed-Won"]
- [e.g., "Non-US operations — we've never closed international"]

## Confidence notes
- **Strong signal:** [patterns that survived all 3 rounds cleanly]
- **Soft signal:** [patterns that only survived the final round, or survived with weak reasoning]
- **Known unknowns:** [dimensions the data didn't cover well — the user should be aware]

## Round log
| Round | Candidates | Kept | Killed | Notable changes |
|-------|-----------|------|--------|-----------------|
| 1 | 127 | 18 | 109 | — |
| 2 | 131 | 22 | 109 | Resurrected "tech_stack=Segment" on interaction evidence |
| 3 | 131 | 22 | 109 | Converged (0 changes) |

**Killed patterns worth reviewing manually:**
- [id]: [kill reason] — if you think this matters, add it back before scoring.
- ...
```

The Round log is load-bearing. The user reads it to decide whether to resurrect a killed pattern before scoring.

## Anti-patterns

- Do NOT run more than 3 rounds.
- Do NOT write `scoring/*` files.
- Do NOT query external APIs.
- Do NOT edit the raw Closed-Won CSV.
- Do NOT skip writing `target-description.md` even if few patterns survived.

## Hand-off

After writing `target-description.md`, print to user: `"Target description written to data/target-description.md. Review the Round log — especially the killed patterns worth reviewing. When ready, invoke account-search to pull a raw account list."`
````

- [ ] **Step 3: Validate frontmatter**

Run:
```bash
python3 -c "
import re, yaml
with open('.claude/skills/pattern-antagonist-loop/SKILL.md') as f:
    content = f.read()
m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
fm = yaml.safe_load(m.group(1))
assert fm['name'] == 'pattern-antagonist-loop'
print('OK')
"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/pattern-antagonist-loop/SKILL.md
git commit -m "Add pattern-antagonist-loop orchestrator skill"
```

---

## Task 5: Skill — `account-search` (with provider adapter pattern)

**Files:**
- Create: `.claude/skills/account-search/SKILL.md`
- Create: `.claude/skills/account-search/providers/README.md`
- Create: `.claude/skills/account-search/providers/apollo.md`
- Create: `.claude/skills/account-search/providers/ocean.md`
- Create: `.claude/skills/account-search/providers/clay.md`
- Create: `.claude/skills/account-search/providers/databar.md`
- Create: `.claude/skills/account-search/providers/exa.md`
- Create: `.claude/skills/account-search/providers/fullenrich.md`
- Create: `.claude/skills/account-search/providers/store-leads.md`

- [ ] **Step 1: Create directory structure**

Run: `mkdir -p .claude/skills/account-search/providers`

- [ ] **Step 2: Write main `SKILL.md`**

Create `.claude/skills/account-search/SKILL.md`:

````markdown
---
name: account-search
description: Use after data/target-description.md exists and the user wants to pull a wide raw account list from GTM databases (Apollo, Ocean, Clay, Databar, Exa, FullEnrich, Store Leads). Translates the target description into provider-specific search queries, runs them, writes raw results to data/accounts-raw/. Remix-able — users add their own provider adapters.
---

# Account Search Skill

## Your role

Turn `data/target-description.md` into wide queries against GTM databases. Pull raw accounts. Write the results to `data/accounts-raw/`. Do not score, filter, or tier — that's for account-scoring.

## Preconditions

1. `data/target-description.md` exists.
2. At least one provider under `.claude/skills/account-search/providers/*.md` (other than `README.md`) describes a provider the user has credentials for. Environment variables expected per provider are documented in each provider file.

## Provider registry

Read every `.md` file under `.claude/skills/account-search/providers/` (except `README.md`). Each one describes a single provider: what it's good for, its filter schema, how to translate target-description fields into its filters, its API endpoint or MCP server, and any rate-limit notes.

**This is the remix surface.** If the user has added their own `my-provider.md`, you pick it up automatically.

## How to query

1. Read `data/target-description.md`. Extract the firmographic signature and disqualifiers.
2. Check environment variables to decide which providers are configured. Skip providers without credentials.
3. For each configured provider:
   - Translate the firmographic signature into that provider's filter schema (the provider file tells you how).
   - Run the query.
   - Write results to `data/accounts-raw/{provider}-{YYYYMMDD-HHMMSS}.csv`.
4. After all providers run, write a manifest at `data/accounts-raw/manifest.json`:

```json
{
  "run_at": "2026-04-23T14:32:01Z",
  "target_description_source": "data/target-description.md",
  "providers_run": [
    {
      "provider": "apollo",
      "result_count": 47213,
      "filters_used": { "... provider-specific ..." },
      "output_file": "data/accounts-raw/apollo-20260423-143201.csv"
    }
  ],
  "total_unique_domains": 52817
}
```

5. Dedupe across providers **by domain** (canonical, lowercased, no www). The deduped master list goes into `data/accounts-raw/deduped-{YYYYMMDD-HHMMSS}.csv`.

## Wide, not narrow

Goal is tens of thousands to millions of rows. **If a query returns fewer than 500 results, relax filters and retry.** Note the relaxation in the manifest. Tight filters at search time defeat the purpose — scoring is where narrowing happens.

## Anti-patterns

- Do NOT score, tier, or filter results. Raw is the point.
- Do NOT enrich results beyond what providers return natively.
- Do NOT dedupe against the user's CRM — that's a separate step the user owns.
- Do NOT call `account-scoring` or write `scoring/*`.
- Do NOT invent providers not represented by a `.md` file in `providers/`.

## When done

Print: `"Pulled N unique accounts across M providers. Deduped master list: data/accounts-raw/deduped-{timestamp}.csv. Run account-scoring next."`
````

- [ ] **Step 3: Write providers `README.md`**

Create `.claude/skills/account-search/providers/README.md`:

````markdown
# Account Search Providers

One markdown file per provider. The `account-search` skill reads all files in this directory (except this README) and uses them to query GTM databases.

## Adding a new provider

Create `my-provider.md` with this structure:

```markdown
# <Provider Name>

## What it's good for
One or two sentences on which verticals / company types this provider indexes well.

## Credentials
- Environment variable(s) required: `MY_PROVIDER_API_KEY`
- How to obtain: <link or one-liner>

## API / access method
- Endpoint: `https://api.my-provider.com/v1/...`
- Or MCP server: `mcp__my_provider__search`
- Auth: Bearer token in `Authorization` header

## Filter schema
List the filters the provider accepts. Example:
- `industry`: string, one of [SaaS, Fintech, ...]
- `headcount_min`: int
- `headcount_max`: int
- `country`: ISO 3166-1 alpha-2
- `funding_stage`: one of [Seed, Series A, ...]

## Translation from target-description.md
Explain how to map the firmographic signature blocks in `data/target-description.md` to this provider's filters. Be specific:
- "Headcount: 50-500" → `{ "headcount_min": 50, "headcount_max": 500 }`
- "HQ: US Northeast" → `{ "country": "US", "region": ["NY", "MA", "CT", "NJ", "PA"] }`

## Output schema
Which columns the provider returns in its CSV export. Flag which ones map to standard columns (domain, company name, headcount, HQ, funding).

## Rate limits
Per-minute / per-day limits. Recommended batch size. Retry strategy on 429.

## Notes
Anything else — quirks, known-bad filters, special behavior.
```

## Provider files in this directory

- `apollo.md` — Apollo.io
- `ocean.md` — Ocean.io
- `clay.md` — Clay (via workspace + webhook)
- `databar.md` — Databar
- `exa.md` — Exa (Exa.ai)
- `fullenrich.md` — FullEnrich
- `store-leads.md` — Store Leads (ecom-specific)
````

- [ ] **Step 4: Write individual provider stubs**

For each of the 7 provider files below, create the file with ONLY the "scaffold" content — enough that a user knows this provider is supported and where to fill in the real credentials/mapping. Real filter schemas will evolve; the scaffold is what ships in v1.

Create `.claude/skills/account-search/providers/apollo.md`:

````markdown
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
````

Create `.claude/skills/account-search/providers/ocean.md`:

````markdown
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
````

Create `.claude/skills/account-search/providers/clay.md`:

````markdown
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
````

Create `.claude/skills/account-search/providers/databar.md`:

````markdown
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
````

Create `.claude/skills/account-search/providers/exa.md`:

````markdown
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
````

Create `.claude/skills/account-search/providers/fullenrich.md`:

````markdown
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
````

Create `.claude/skills/account-search/providers/store-leads.md`:

````markdown
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
````

- [ ] **Step 5: Validate all skill + provider files**

Run:
```bash
python3 -c "
import re, yaml, glob, os
# Validate main SKILL.md
with open('.claude/skills/account-search/SKILL.md') as f:
    content = f.read()
m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
fm = yaml.safe_load(m.group(1))
assert fm['name'] == 'account-search'
# Count provider files
providers = [p for p in glob.glob('.claude/skills/account-search/providers/*.md') if not p.endswith('README.md')]
assert len(providers) == 7, f'Expected 7 providers, found {len(providers)}'
# Every provider file must exist and be nonempty
for p in providers:
    assert os.path.getsize(p) > 200, f'{p} is too small'
print(f'OK — 7 providers: {sorted([os.path.basename(p) for p in providers])}')
"
```
Expected: `OK — 7 providers: [...]`

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/account-search/
git commit -m "Add account-search skill with 7 provider adapters"
```

---

## Task 6: Skill — `account-scoring`

**Files:**
- Create: `.claude/skills/account-scoring/SKILL.md`

- [ ] **Step 1: Create directory**

Run: `mkdir -p .claude/skills/account-scoring`

- [ ] **Step 2: Write `SKILL.md`**

Create `.claude/skills/account-scoring/SKILL.md`:

````markdown
---
name: account-scoring
description: Use after data/target-description.md exists and the user wants to generate or run a scoring algorithm that turns the description into tiers (T1/T2/T3/T4). Two modes — (1) generate scoring/rules.py + scoring/rules.md + scoring/weights.yaml from the target description, or (2) run the existing scoring/ against data/accounts-raw/ and write data/accounts-scored/tiered.csv. Human is expected to hand-tweak weights and hard-code rules after generation.
---

# Account Scoring Skill

## Your role

Two modes:
- **Generate mode:** Turn `data/target-description.md` into a concrete scoring algorithm under `scoring/`.
- **Run mode:** Execute the algorithm against the raw account list to produce tiers, then sense-check against the user's own Closed-Won.

You are NOT expected to produce a perfect algorithm on the first pass. The human will hand-edit `scoring/weights.yaml` and probably `scoring/rules.py`. Design for iteration.

## Mode selection

- If `scoring/rules.py` does not exist → **Generate mode.**
- If `scoring/rules.py` exists AND `data/accounts-raw/` contains at least one `.csv` → **Run mode.**
- If both exist and the user has not explicitly asked to regenerate → **Run mode**, with a warning: *"scoring/ already exists. If you want to regenerate from a new target description, delete scoring/rules.py first or explicitly ask to regenerate."*
- **Never silently overwrite `scoring/*`.** Regeneration is always explicit.

---

## Generate mode

Read `data/target-description.md`. Produce three files:

### `scoring/rules.py`

Pure Python. Each rule is a function that takes a single row (dict with column name → value) and returns either a numeric score or a boolean. One function per pattern from the target description. Every function has a one-line docstring stating which pattern it implements.

Example shape:

```python
"""Deterministic scoring rules. Generated from data/target-description.md.
Hand-edit freely — this file is yours."""

def headcount_in_target_band(row: dict) -> bool:
    """Firmographic signature: Headcount 50-500."""
    try:
        hc = int(row.get("headcount", 0))
    except (TypeError, ValueError):
        return False
    return 50 <= hc <= 500

def hq_in_target_region(row: dict) -> bool:
    """Firmographic signature: HQ in US Northeast."""
    return row.get("hq_state", "").upper() in {"NY", "MA", "CT", "NJ", "PA", "RI", "VT", "NH", "ME"}

# Disqualifier
def is_public_company(row: dict) -> bool:
    """Disqualifier: public companies — our Closed-Won is 100% private."""
    return row.get("ownership_type", "").lower() == "public"
```

### `scoring/rules.md`

LLM-rules: narrative description of the rules that require classification, web research, or judgment that deterministic code can't do. The run-mode engine uses this to know when to call out to a model.

Shape:

```markdown
# LLM-assisted scoring rules

## rule: sells_to_smb
Use when we need to classify whether a company sells primarily to SMBs (<500 employees) vs. enterprise. Deterministic data rarely captures this directly. Research the company's website and case studies if available. Return boolean.

## rule: has_ai_positioning
Does the company position itself as AI-native or AI-forward in current marketing? Research homepage + recent blog posts.
```

### `scoring/weights.yaml`

YAML with one entry per rule (both py and md), plus threshold config. Header comment must include: `# TWEAK THIS. These weights are a starting hypothesis, not gospel. Your judgment beats the LLM's.`

Shape:

```yaml
# TWEAK THIS. These weights are a starting hypothesis, not gospel.
# Your judgment beats the LLM's.
#
# Total possible score = sum of all positive weights when all rules return True.
# Disqualifier rules (negative weights or boolean-gated) can zero out a score entirely.

rules:
  headcount_in_target_band:
    weight: 25
    type: boolean
    description: "Firmographic: headcount 50-500"

  hq_in_target_region:
    weight: 20
    type: boolean
    description: "Firmographic: US Northeast"

  is_public_company:
    weight: -1000   # effective disqualifier
    type: boolean
    description: "Disqualifier: public company"

  sells_to_smb:
    weight: 15
    type: llm
    description: "Classification: sells to SMB"

# Tier thresholds (percentile-based unless hand-picked list is provided)
tiers:
  sense_check_threshold: 0.80   # at least 80% of Closed-Won must land in T1 or T2
  t1:
    percentile_min: 0.99         # top 1%
    named_accounts_file: null    # optional path to hand-picked list (csv with domain column)
  t2:
    percentile_min: 0.90         # top 10% (excluding T1)
  t3:
    percentile_min: 0.60         # top 40% (excluding T1/T2)
  t4:
    score_floor: 10              # minimum score to make T4 at all (else excluded from output)
```

Print after generating: `"scoring/ generated. Hand-edit weights.yaml and rules.py to match your judgment, then re-run this skill to score."`

---

## Run mode

1. **Normalize columns.** Read `data/accounts-raw/deduped-*.csv` (or the most recent file matching that pattern). Compare its columns to `data/closed-won/*.csv`. Map columns so that the rules in `scoring/rules.py` can run against raw-account rows. If there's no clean mapping for a column a rule needs, surface the gap to the user and stop.

2. **Apply deterministic rules.** For each row, run every function in `scoring/rules.py`.

3. **Apply LLM rules.** For each rule in `scoring/rules.md`, call out to Claude (or whichever model the user has configured) as described in the rule body. Cache results by domain in `data/accounts-scored/.llm-cache.json` to avoid re-billing on re-runs.

4. **Compute weighted score.** For each row, sum `weight * rule_result` across all rules. Disqualifier rules with large negative weights zero out the score effectively.

5. **Assign tiers** per `weights.yaml` thresholds. Named accounts (if a file is provided) always become T1.

6. **Write `data/accounts-scored/tiered.csv`** with columns:
   - All original columns from the raw list
   - `score` (numeric)
   - `tier` (T1 | T2 | T3 | T4 | excluded)
   - `top_rules` (comma-joined: top 3 contributing rules + their weighted contributions)

7. **Sense-check gate — REQUIRED, DO NOT SKIP.**
   - Run the same scoring pipeline against `data/closed-won/*.csv`.
   - Compute share of Closed-Won rows landing in T1 or T2.
   - Read threshold from `weights.yaml → tiers.sense_check_threshold` (default 0.80).
   - If share < threshold: emit loud warning:
     ```
     ⚠️  SENSE-CHECK FAILED
     Only X% of your Closed-Won landed in T1/T2 (threshold: Y%).
     Your algorithm does not recognize your own best customers.
     Before trusting data/accounts-scored/tiered.csv:
       - Review which Closed-Won companies were misclassified (see data/accounts-scored/closed-won-sense-check.csv)
       - Re-weight rules in scoring/weights.yaml
       - Consider hard-coding rules for edge cases
       - Re-run this skill
     ```
   - Write `data/accounts-scored/closed-won-sense-check.csv` with each Closed-Won row, its computed score, its tier, and top_rules. This is the audit trail.
   - If share >= threshold: print `"Sense-check passed: X% of Closed-Won in T1/T2."`

## Anti-patterns

- Do NOT silently rewrite `scoring/weights.yaml` on re-runs. User owns that file.
- Do NOT skip the sense-check.
- Do NOT produce a single-tier output. Tiers are the point.
- Do NOT call external APIs inside `scoring/rules.py` — deterministic rules are local Python only. External calls belong in `rules.md`.
- Do NOT pretend LLM rules succeeded when they failed silently. Cache errors and surface them.

## When done (run mode)

Print:
```
Scored N accounts. Distribution:
  T1: A  (B%)
  T2: C  (D%)
  T3: E  (F%)
  T4: G  (H%)
Sense-check: [PASSED / FAILED with X% vs threshold Y%]
Output: data/accounts-scored/tiered.csv
```
````

- [ ] **Step 3: Validate frontmatter**

Run:
```bash
python3 -c "
import re, yaml
with open('.claude/skills/account-scoring/SKILL.md') as f:
    content = f.read()
m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
fm = yaml.safe_load(m.group(1))
assert fm['name'] == 'account-scoring'
print('OK')
"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/account-scoring/SKILL.md
git commit -m "Add account-scoring skill with generate/run modes and sense-check gate"
```

---

## Task 7: Example artifacts

**Files:**
- Create: `examples/closed-won-sample.csv`
- Create: `examples/target-description-sample.md`
- Create: `examples/scoring-algorithm-sample/rules.py`
- Create: `examples/scoring-algorithm-sample/rules.md`
- Create: `examples/scoring-algorithm-sample/weights.yaml`

- [ ] **Step 1: Create example directory**

Run: `mkdir -p examples/scoring-algorithm-sample`

- [ ] **Step 2: Write `closed-won-sample.csv`**

Create `examples/closed-won-sample.csv` with 30 synthetic rows representing a fictional B2B SaaS company's Closed-Won. Include columns: `company_name, domain, headcount, hq_city, hq_state, hq_country, industry, funding_stage, ownership_type, tech_stack, estimated_arr_usd, closed_won_date`.

Content:
```csv
company_name,domain,headcount,hq_city,hq_state,hq_country,industry,funding_stage,ownership_type,tech_stack,estimated_arr_usd,closed_won_date
Acme Growth,acmegrowth.com,120,New York,NY,US,SaaS,Series B,Private,"Segment,Snowflake,dbt",2400000,2025-01-14
Beacon Analytics,beacon.io,85,Boston,MA,US,Analytics,Series A,Private,"Segment,Looker",1200000,2025-01-28
Compass Retail,compassretail.com,230,Brooklyn,NY,US,Retail Tech,Series B,Private,"Segment,Snowflake,Heap",3100000,2025-02-03
Driftwood AI,driftwood.ai,45,San Francisco,CA,US,AI,Seed,Private,"Segment,Hex",450000,2025-02-11
Everbloom Labs,everbloom.co,180,New York,NY,US,MarTech,Series B,Private,"Segment,Snowflake,dbt,Census",2800000,2025-02-19
Fathom Data,fathomdata.com,95,Brooklyn,NY,US,Data Infra,Series A,Private,"Snowflake,dbt",1600000,2025-02-26
Glowforge SaaS,glowforge-saas.com,310,Chicago,IL,US,SaaS,Series C,Private,"Segment,Snowflake",4200000,2025-03-04
Harbor Pay,harborpay.com,140,New York,NY,US,Fintech,Series B,Private,"Segment,Snowflake,Heap",2500000,2025-03-09
Indigo CX,indigocx.com,65,Cambridge,MA,US,CX,Series A,Private,"Segment,Looker",980000,2025-03-14
Juno Cloud,junocloud.io,220,New York,NY,US,DevTools,Series B,Private,"Segment,Snowflake,dbt",3000000,2025-03-20
Kite ML,kite-ml.com,50,San Francisco,CA,US,AI,Seed,Private,"Segment,Hex",600000,2025-03-25
Lantern Grow,lanterngrow.com,175,Jersey City,NJ,US,MarTech,Series B,Private,"Segment,Snowflake,Census",2700000,2025-04-02
Mercury Ops,mercuryops.com,110,Boston,MA,US,DevOps,Series A,Private,"Segment,Snowflake",1800000,2025-04-08
Northwind Data,northwind.io,260,New York,NY,US,Data Infra,Series C,Private,"Snowflake,dbt,Hightouch",3800000,2025-04-15
Onyx Retention,onyxretention.com,75,Manhattan,NY,US,MarTech,Series A,Private,"Segment,Looker,Heap",1100000,2025-04-21
Paloma Commerce,palomacommerce.com,195,New York,NY,US,Commerce,Series B,Private,"Segment,Snowflake,dbt",2900000,2025-05-01
Quill Insights,quillinsights.com,130,Brooklyn,NY,US,Analytics,Series B,Private,"Segment,Snowflake,dbt,Hex",2300000,2025-05-09
Ripple Checkout,ripplecheckout.com,85,New York,NY,US,Fintech,Series A,Private,"Segment,Heap",1400000,2025-05-14
Sable Tracking,sabletracking.com,155,Boston,MA,US,Analytics,Series B,Private,"Segment,Snowflake",2600000,2025-05-22
Turret Security,turretsec.com,290,Austin,TX,US,Security,Series C,Private,"Segment,Snowflake",3500000,2025-06-03
Umbra Mail,umbramail.com,70,New York,NY,US,MarTech,Series A,Private,"Segment,Looker",1050000,2025-06-10
Verve Analytics,verve-analytics.com,200,Cambridge,MA,US,Analytics,Series B,Private,"Segment,Snowflake,dbt,Hex",2850000,2025-06-17
Willow Pay,willowpay.com,115,New York,NY,US,Fintech,Series B,Private,"Segment,Snowflake",2200000,2025-06-24
Xenon Attribution,xenonattribution.com,165,Brooklyn,NY,US,MarTech,Series B,Private,"Segment,Snowflake,dbt,Census",2750000,2025-07-01
Yarrow CDP,yarrow-cdp.com,105,Boston,MA,US,MarTech,Series A,Private,"Segment,Snowflake",1700000,2025-07-08
Zephyr Pipelines,zephyrpipes.com,240,New York,NY,US,Data Infra,Series C,Private,"Snowflake,dbt,Hightouch,Census",3600000,2025-07-15
Atlas Personalize,atlaspersonalize.com,90,Jersey City,NJ,US,MarTech,Series A,Private,"Segment,Heap,Looker",1350000,2025-07-23
Bramble Forecast,brambleforecast.com,135,New York,NY,US,Analytics,Series B,Private,"Segment,Snowflake,dbt",2450000,2025-07-30
Cirrus Warehouse,cirruswarehouse.com,210,Brooklyn,NY,US,Data Infra,Series B,Private,"Snowflake,dbt",3100000,2025-08-06
Delta Retain,deltaretain.com,80,Boston,MA,US,MarTech,Series A,Private,"Segment,Looker,Heap",1250000,2025-08-13
```

- [ ] **Step 3: Write `target-description-sample.md`**

Create `examples/target-description-sample.md`:

````markdown
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
````

- [ ] **Step 4: Write `scoring-algorithm-sample/rules.py`**

Create `examples/scoring-algorithm-sample/rules.py`:

```python
"""Deterministic scoring rules. Generated from data/target-description.md.
Hand-edit freely — this file is yours."""


def headcount_in_target_band(row: dict) -> bool:
    """Firmographic signature: headcount 50-300."""
    try:
        hc = int(row.get("headcount", 0))
    except (TypeError, ValueError):
        return False
    return 50 <= hc <= 300


def hq_in_northeast(row: dict) -> bool:
    """Firmographic signature: HQ in US Northeast."""
    return row.get("hq_state", "").upper() in {
        "NY", "MA", "CT", "NJ", "PA", "RI", "VT", "NH", "ME",
    }


def is_venture_backed(row: dict) -> bool:
    """Firmographic signature: private + institutional funding (Series A-C)."""
    ownership = row.get("ownership_type", "").lower()
    stage = row.get("funding_stage", "").lower()
    return ownership == "private" and any(
        s in stage for s in ("series a", "series b", "series c")
    )


def has_segment_in_stack(row: dict) -> bool:
    """Firmographic signature: Segment in tech stack (85% match rate in Closed-Won)."""
    stack = (row.get("tech_stack") or "").lower()
    return "segment" in stack


def has_modern_data_stack(row: dict) -> bool:
    """Interaction pattern: Snowflake AND dbt together in stack."""
    stack = (row.get("tech_stack") or "").lower()
    return "snowflake" in stack and "dbt" in stack


def in_target_industry(row: dict) -> bool:
    """Firmographic signature: MarTech / Analytics / Data Infra / Fintech."""
    industry = (row.get("industry") or "").lower()
    return any(
        kw in industry
        for kw in ("martech", "analytics", "data infra", "fintech", "commerce", "devtools")
    )


# Disqualifiers
def is_public(row: dict) -> bool:
    """Disqualifier: public companies — Closed-Won is 100% private."""
    return (row.get("ownership_type") or "").lower() == "public"


def is_non_us(row: dict) -> bool:
    """Disqualifier: non-US HQ."""
    country = (row.get("hq_country") or "").upper()
    return country not in ("", "US", "USA", "UNITED STATES")
```

- [ ] **Step 5: Write `scoring-algorithm-sample/rules.md`**

Create `examples/scoring-algorithm-sample/rules.md`:

````markdown
# LLM-assisted scoring rules

These rules require classification or web research that deterministic code can't do reliably. The run-mode engine calls these out to a model, caching results by domain.

## rule: sells_to_data_teams

Use when we need to classify whether the company's primary buyer is a data/analytics/engineering team (vs. marketing, sales, or ops). Look at the company's homepage, customer logos, and any recent case studies. Return boolean.

## rule: modern_brand_positioning

Does the company position itself as modern / developer-friendly / AI-native in current marketing (homepage, recent blog posts)? Return boolean. This is soft signal — it correlates with fit but isn't deterministic.

## rule: likely_in_buying_window

Based on recent public signals (funding news within 6 months, new exec hires in data/analytics/RevOps roles, tech stack expansion), is this company likely in a buying window for our product? Use your judgment — return `"active" | "cooling" | "unknown"`.
````

- [ ] **Step 6: Write `scoring-algorithm-sample/weights.yaml`**

Create `examples/scoring-algorithm-sample/weights.yaml`:

```yaml
# TWEAK THIS. These weights are a starting hypothesis, not gospel.
# Your judgment beats the LLM's.
#
# Total possible score when all positive rules return True ≈ 145.
# Disqualifier rules zero out the score via large negative weights.

rules:
  # Firmographic
  headcount_in_target_band:
    weight: 25
    type: boolean
    description: "Headcount 50-300"
  hq_in_northeast:
    weight: 20
    type: boolean
    description: "HQ in US Northeast"
  is_venture_backed:
    weight: 15
    type: boolean
    description: "Private + Series A-C"
  in_target_industry:
    weight: 15
    type: boolean
    description: "MarTech / Analytics / Data Infra / Fintech"

  # Tech stack (strongest single signal)
  has_segment_in_stack:
    weight: 30
    type: boolean
    description: "Segment in tech stack"
  has_modern_data_stack:
    weight: 20
    type: boolean
    description: "Snowflake + dbt together"

  # Disqualifiers
  is_public:
    weight: -1000
    type: boolean
    description: "Disqualifier: public company"
  is_non_us:
    weight: -1000
    type: boolean
    description: "Disqualifier: non-US HQ"

  # LLM-assisted
  sells_to_data_teams:
    weight: 20
    type: llm
    description: "Sells to data/analytics/eng buyer"
  modern_brand_positioning:
    weight: 10
    type: llm
    description: "Modern / developer-friendly positioning"

# Tier thresholds
tiers:
  sense_check_threshold: 0.80   # at least 80% of Closed-Won must land in T1 or T2
  t1:
    percentile_min: 0.99
    named_accounts_file: null
  t2:
    percentile_min: 0.90
  t3:
    percentile_min: 0.60
  t4:
    score_floor: 10
```

- [ ] **Step 7: Commit**

```bash
git add examples/
git commit -m "Add example artifacts: synthetic Closed-Won, target description, scoring algorithm"
```

---

## Task 8: Write the README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Read current `README.md`**

Run: `cat README.md`. (Currently just a WIP placeholder.)

- [ ] **Step 2: Overwrite `README.md`**

Write the following to `README.md`:

````markdown
# Antagonistic Agents in Account Building

> Fork this. Point it at your Closed-Won. Watch two AI agents argue.
> Walk away with a tiered account list in days, not months.

Companion repo to Elliot Roazen's talk at **NYC GTM 2026**.
Slides & recording: _(add link after talk)_.

---

## The thesis (90 seconds)

AI has two flaws. It's **agreeable**. It **overproduces**.

This repo fights both by pitting two Claude Code skills against each other:

- **Pattern Recognition** surfaces every pattern in your Closed-Won. Noisy by design.
- **Antagonist** kills the patterns that don't actually change a GTM decision. Skeptical by design.

You set up the fight. You read the result. That's the whole game.

---

## What you need

- [Claude Code](https://docs.claude.com/en/docs/claude-code) installed
- A Closed-Won export from your CRM (HubSpot / Salesforce / Attio)
- An enrichment tool (Clay / Databar / Exa / FullEnrich / Store Leads)
- API keys for at least one account database (Apollo / Ocean / etc.) set as environment variables

---

## Quick start

```bash
git clone https://github.com/gunsandroazen/antagonistic-agent-account-building
cd antagonistic-agent-account-building
# Drop your enriched Closed-Won CSV into data/closed-won/
# Then in Claude Code:
/skill pattern-antagonist-loop
```

That's the core loop. Everything below expands the full 7 steps.

---

## The 7 steps (mirrors the talk)

### 1. Pull Closed-Won from your CRM

Focus on properties that (a) matter and (b) are accurate. Every CRM is different.

If you're mature, segment by offering or customer type. Drop the CSV into `data/closed-won/` (only one file at a time).

### 2. Enrich to the n-th degree

Use Clay, Databar, Exa, FullEnrich, or your weapon of choice. For ecom, Store Leads.
Goal: wide variety of data points, high completeness, real quality.

Save the enriched result in `data/closed-won/`, replacing the raw CRM file.

### 3. Run the pattern↔antagonist loop

```
/skill pattern-antagonist-loop
```

Runs `pattern-recognition` → `antagonist` up to 3 rounds. Writes:
- `data/patterns/candidates-r{1,2,3}.json`
- `data/patterns/survivors-r{1,2,3}.json`
- `data/target-description.md` ← **this is the artifact**

**Read the Round log** at the bottom of `target-description.md`. If the antagonist killed something you'd defend, resurrect it manually before moving on.

### 4. Convert the description into a search + scoring

```
/skill account-search            # wide pull from Apollo / Ocean / etc.
/skill account-scoring           # generates scoring/ files from the description
```

Then hand-edit `scoring/weights.yaml` and `scoring/rules.py`.

> You are smarter than the LLM. This is where that matters.

### 5. Re-enrich and score → tiers

```
/skill account-scoring           # now in run mode
```

Writes `data/accounts-scored/tiered.csv` with T1–T4, scores, and the top-3 rules contributing to each row's score.

**The skill will also sense-check against your Closed-Won.** If <80% of your own best customers land in T1/T2, the skill will warn you loudly — your algorithm is broken. Tweak weights, re-run.

### 6. Go to market

Outbound. Inbound. Ads. ABM. Dinners.

### 7. Feedback → inputs → re-run

Tiers are a hypothesis. GTM results are inputs back into the system. Re-run the loop quarterly, or whenever your Closed-Won has shifted meaningfully.

---

## Directory map

```
.
├── .claude/skills/                 # the 5 skills
│   ├── pattern-recognition/
│   ├── antagonist/
│   ├── pattern-antagonist-loop/
│   ├── account-search/
│   │   └── providers/              # one .md per provider — drop yours in
│   └── account-scoring/
├── data/                           # gitignored — your Closed-Won never leaves local
│   ├── closed-won/                 # INPUT: your enriched CSV
│   ├── patterns/                   # pattern+survivor JSON (per round)
│   ├── target-description.md       # OUTPUT of the loop
│   ├── accounts-raw/               # OUTPUT of account-search
│   └── accounts-scored/            # OUTPUT of account-scoring
├── scoring/                        # your algorithm — hand-edit, commit to your fork
│   ├── rules.py                    # deterministic rules (generated, you tweak)
│   ├── rules.md                    # LLM rules (generated, you tweak)
│   └── weights.yaml                # weights + thresholds (generated, you tweak)
└── examples/                       # teaching material — check this out first
    ├── closed-won-sample.csv
    ├── target-description-sample.md
    └── scoring-algorithm-sample/
```

---

## The skills

| Skill | Reads | Writes |
|---|---|---|
| `pattern-recognition` | `data/closed-won/*.csv` | `data/patterns/candidates.json` |
| `antagonist` | `data/patterns/candidates.json` | `data/patterns/survivors.json` |
| `pattern-antagonist-loop` | `data/closed-won/*.csv` | `data/target-description.md` |
| `account-search` | `data/target-description.md` | `data/accounts-raw/*.csv` |
| `account-scoring` (generate) | `data/target-description.md` | `scoring/rules.py, rules.md, weights.yaml` |
| `account-scoring` (run) | `scoring/*`, `data/accounts-raw/*.csv` | `data/accounts-scored/tiered.csv` |

---

## Remixing

- **Add a GTM provider:** drop `my-provider.md` in `.claude/skills/account-search/providers/`. Format is documented in `providers/README.md`. The skill picks it up automatically.
- **Tweak scoring:** `scoring/weights.yaml` is yours. Hard-code rules in `scoring/rules.py`. Add LLM research steps in `scoring/rules.md`.
- **Change the antagonist's posture:** edit `.claude/skills/antagonist/SKILL.md`. Kill-by-default is intentional — softening it loses the point.

---

## FAQ / gotchas

**The antagonist killed a pattern I know matters.**
Good — that means it's doing its job. Check the Round log in `target-description.md` — often a killed pattern is resurrected in round 2 or 3 after a grudge argument. If not, restore it manually before scoring.

**The loop ran 3 rounds and didn't converge.**
Your Closed-Won is probably too heterogeneous. Segment by offering or customer type and run each segment separately.

**<80% of my Closed-Won landed in T1/T2.**
Your scoring algorithm is broken. The skill will warn you. Start by re-weighting in `weights.yaml`, then add hard-coded rules in `rules.py` for edge cases.

**GTM tool credits are expensive.**
Exactly. That's why we iterate in a repo + CSVs + Claude Code, and only hit credit-based tools when we're confident. That's the whole stack philosophy.

**Can I use this for person-level ICP, not just accounts?**
Not in v1. The patterns and scoring are account-level. Person-level enrichment happens after you have the tiered list, using your existing tools.

---

## Ethics + data handling

Your Closed-Won is customer data. Treat it accordingly:

- `data/` is gitignored in this repo — your raw data never leaves your machine via git.
- If you fork and add any `data/` files, **audit your fork's `.gitignore`** before pushing.
- Even better: sanitize or anonymize before running the loop. Domain + firmographic features are usually enough; you don't need customer PII.
- Don't paste Closed-Won CSVs into external chat tools. Run the skills locally via Claude Code.

---

## License

MIT — see [LICENSE](./LICENSE).

---

## Built by

[**Elliot Roazen**](https://linkedin.com/in/elliotroazen) · Head of Growth, [Prescient AI](https://prescientai.com)
Questions / hate mail / success stories: elliot@prescientai.com
````

- [ ] **Step 3: Verify structure**

Run:
```bash
wc -l README.md
grep -c "^## " README.md
```
Expected: README is substantive (>200 lines) and has multiple top-level sections.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "Write README — 7-step walkthrough mirroring the talk"
```

---

## Task 9: Final verification

**Files:** (read-only validation)

- [ ] **Step 1: Tree check**

Run:
```bash
find . -type f -not -path './.git/*' | sort
```
Expected output includes all of:
```
./.claude/skills/account-scoring/SKILL.md
./.claude/skills/account-search/SKILL.md
./.claude/skills/account-search/providers/README.md
./.claude/skills/account-search/providers/apollo.md
./.claude/skills/account-search/providers/clay.md
./.claude/skills/account-search/providers/databar.md
./.claude/skills/account-search/providers/exa.md
./.claude/skills/account-search/providers/fullenrich.md
./.claude/skills/account-search/providers/ocean.md
./.claude/skills/account-search/providers/store-leads.md
./.claude/skills/antagonist/SKILL.md
./.claude/skills/pattern-antagonist-loop/SKILL.md
./.claude/skills/pattern-recognition/SKILL.md
./.gitignore
./LICENSE
./README.md
./data/accounts-raw/.gitkeep
./data/accounts-scored/.gitkeep
./data/closed-won/.gitkeep
./data/patterns/.gitkeep
./docs/superpowers/plans/2026-04-23-antagonistic-agents-repo.md
./docs/superpowers/specs/2026-04-23-antagonistic-agents-repo-design.md
./examples/closed-won-sample.csv
./examples/scoring-algorithm-sample/rules.md
./examples/scoring-algorithm-sample/rules.py
./examples/scoring-algorithm-sample/weights.yaml
./examples/target-description-sample.md
./scoring/.gitkeep
```

- [ ] **Step 2: Every SKILL.md parses**

Run:
```bash
python3 -c "
import re, yaml, glob
skills = glob.glob('.claude/skills/*/SKILL.md')
assert len(skills) == 5, f'Expected 5 skills, got {len(skills)}'
for s in skills:
    with open(s) as f:
        content = f.read()
    m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    assert m, f'{s}: no frontmatter'
    fm = yaml.safe_load(m.group(1))
    assert 'name' in fm and 'description' in fm, f'{s}: missing name/description'
    assert len(fm['description']) > 50, f'{s}: description too short'
    print(f'{fm[\"name\"]}: OK ({len(fm[\"description\"])} char desc)')
print('All skills valid.')
"
```
Expected: 5 skills listed, all OK.

- [ ] **Step 3: `.gitignore` is effective**

Run:
```bash
echo "secret_customers" > data/closed-won/fake.csv
git status --short data/
rm data/closed-won/fake.csv
```
Expected: `git status` shows nothing for `data/` (beyond `.gitkeep` files).

- [ ] **Step 4: Push to origin**

```bash
git push origin main
```
Expected: push succeeds. Verify at https://github.com/gunsandroazen/antagonistic-agent-account-building

- [ ] **Step 5: Final commit (only if there's anything unstaged)**

```bash
git status
```
Expected: `nothing to commit, working tree clean`. If anything is outstanding, commit it with a descriptive message, then push again.

---

## Self-review checklist (for the implementer to run at the end)

- [ ] All 5 skills exist and frontmatter parses.
- [ ] `account-search` has 7 provider files + 1 README.
- [ ] `examples/` has a 30-row CSV, a target description, and a complete scoring algorithm (py + md + yaml).
- [ ] `data/` contents are gitignored; `.gitkeep` files are tracked.
- [ ] `scoring/` is empty except for `.gitkeep` (the main template; user forks populate it via Generate mode).
- [ ] README walks through all 7 steps from the talk.
- [ ] No TODO / TBD / "fill in later" anywhere in the repo.
- [ ] `git push origin main` succeeded; public repo reflects everything.
