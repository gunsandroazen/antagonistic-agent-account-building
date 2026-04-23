# Antagonistic Agents in Account Building — Repo Design Spec

**Date:** 2026-04-23
**Author:** Elliot Roazen (design via Claude Code brainstorm)
**Status:** Approved, ready for implementation planning
**Companion artifact to:** `Antagonistic Agents in Account Building` talk, NYC GTM 2026

---

## 1. Purpose

Public, MIT-licensed Claude Code skills repo that attendees of the NYC GTM 2026 talk can fork and use to execute the 7-step account-building pipeline demonstrated on stage. Audience is ~300 external GTM operators (non-Prescient) who already use Claude Code / Codex / Gemini.

The repo must deliver the exact artifact described in the talk: fork it, drop in a Closed-Won CSV, invoke a small set of skills, and walk away with a tiered account list — with the pattern↔antagonist fight doing the real work.

## 2. Thesis (non-negotiable)

AI has two flaws the repo exists to fight:
1. **Agreeable** — AI defaults to agreement with the user.
2. **Overproduces** — AI rarely says "done"; it adds, expands, rinses tokens.

Every skill in this repo is designed to fight these. The antagonist skill is the sharpest instance, but the bias shows up everywhere: hard round caps on the loop, hard-kill posture on patterns, sense-check gates on scoring, no silent rewrites of user-owned files.

## 3. Scope

**In scope:**
- 5 Claude Code skills (SKILL.md files): `pattern-recognition`, `antagonist`, `pattern-antagonist-loop`, `account-search`, `account-scoring`
- Directory scaffolding the skills read/write against
- README mirroring the 7 steps from the talk
- Example artifacts checked into `examples/` for teaching
- Provider adapter pattern for `account-search` (Apollo / Ocean / Clay / Databar / Exa / FullEnrich / Store Leads)
- Sense-check gate in `account-scoring` that runs the user's algorithm against their own Closed-Won

**Out of scope (v1):**
- Executable Python pipeline / Makefile
- Hosted service or SaaS wrapper
- CRM integrations / automated pulls
- Person-level ICP / contact enrichment
- Outbound / ABM execution tooling
- Feedback loop tooling (GTM results → re-weighting) — documented as a manual step

## 4. Repo layout

```
antagonistic-agent-account-building/
├── README.md
├── LICENSE                                  # MIT
├── .gitignore                               # ignores data/* contents, keeps .gitkeep
│
├── .claude/
│   └── skills/
│       ├── pattern-recognition/SKILL.md
│       ├── antagonist/SKILL.md
│       ├── pattern-antagonist-loop/SKILL.md
│       ├── account-search/
│       │   ├── SKILL.md
│       │   └── providers/
│       │       ├── apollo.md
│       │       ├── ocean.md
│       │       ├── clay.md
│       │       ├── databar.md
│       │       ├── exa.md
│       │       ├── fullenrich.md
│       │       └── store-leads.md
│       └── account-scoring/SKILL.md
│
├── data/                                    # gitignored (contents), .gitkeep checked in
│   ├── closed-won/.gitkeep
│   ├── patterns/.gitkeep
│   ├── target-description.md                # loop output
│   ├── accounts-raw/.gitkeep
│   └── accounts-scored/.gitkeep
│
├── scoring/                                 # user's algorithm — repo ships empty with .gitkeep
│   └── .gitkeep                             # populated by account-scoring skill in Generate mode;
│                                            # user hand-edits thereafter, commits to their fork
│
├── examples/                                # checked in
│   ├── closed-won-sample.csv
│   ├── target-description-sample.md
│   └── scoring-algorithm-sample/
│       ├── rules.py
│       ├── rules.md
│       └── weights.yaml
│
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-04-23-antagonistic-agents-repo-design.md   # this file
```

### Conventions

- **Data flows through known paths** under `data/`. Skills do not take path arguments; they validate known paths and fail loudly if inputs are missing. Matches the "work out of a repo + CSVs + Claude Code" posture from the talk (slide 12).
- **`data/` contents are gitignored** to prevent forks from leaking customer data. Teaching material lives in `examples/`.
- **`scoring/` is checked in** — it represents the user's actual algorithm and evolves with their business. Forks diverge here intentionally.
- **No runtime dependency** beyond Claude Code. `scoring/rules.py` exists as an algorithm; skills invoke it via Bash when needed but do not require a pre-installed Python environment at clone time.
- **Skills are order-validating, not order-enforcing.** Each skill checks its preconditions and exits cleanly if not met.

## 5. Skills

### 5.1 `pattern-recognition`

**Purpose:** Surface every candidate pattern in the Closed-Won CSV. Deliberately noisy.

**Frontmatter:**
```yaml
---
name: pattern-recognition
description: Use when the user has an enriched Closed-Won CSV in data/closed-won/ and wants to surface candidate patterns (location, headcount, ownership, funding, tech stack, HQ, etc.) that might define their best-fit customer. Outputs candidate patterns as JSON to data/patterns/candidates.json. Does NOT decide which patterns matter — that's the antagonist's job.
---
```

**Preconditions:**
- Exactly one `.csv` in `data/closed-won/`. Fail loudly if zero or multiple.
- ≥20 rows, ≥5 columns.

**Behavior:**
- Profile every column: cardinality, distribution, top-N values, numeric bands, null rate.
- For text-heavy columns (descriptions, notes), extract themes.
- Surface interaction effects where obvious (e.g., `hq_city=NYC ∧ funding_stage=Series B`).
- **Bias toward breadth.** Surface dozens to hundreds. Overproduction is intentional here.

**Output contract:** `data/patterns/candidates.json`
```json
{
  "source_file": "data/closed-won/foo.csv",
  "row_count": 847,
  "patterns": [
    {
      "id": "hq_nyc",
      "dimension": "hq_city",
      "claim": "63% of Closed-Won are HQ'd in NYC",
      "evidence": { "match_rate": 0.63, "sample": ["Acme", "Beta"] },
      "hypothesis": "NYC proximity may correlate with fit"
    }
  ]
}
```

**Anti-patterns:**
- Do NOT rank, score, or filter patterns.
- Do NOT write a target description.
- Do NOT edit `scoring/`.

---

### 5.2 `antagonist`

**Purpose:** Kill patterns that don't actually change a GTM decision. Default posture is kill; patterns must earn survival.

**Frontmatter:**
```yaml
---
name: antagonist
description: Use after pattern-recognition to scrutinize every pattern in data/patterns/candidates.json and argue it down to what actually matters. Fights AI's two flaws — agreeable and overproduces. Outputs surviving patterns to data/patterns/survivors.json with explicit kill reasoning for rejects. Adversarial by design — default posture is skepticism.
---
```

**Preconditions:** `data/patterns/candidates.json` exists.

**Posture directive (baked into SKILL.md):** *"Your default is to kill the pattern. You must be convinced it matters. If you cannot write a one-sentence reason this pattern would change a GTM decision, kill it."*

**Four required tests per pattern:**
1. **Decision test:** Would acting on this change who we target or how?
2. **Base-rate test:** Is the claimed match rate meaningfully above the baseline for that dimension?
3. **Coincidence test:** Is this an artifact of how we've historically sold, not a feature of good-fit customers?
4. **Actionability test:** Can a GTM database (Apollo/Ocean/etc.) filter on this? If not, relegate.

**Output contract:** `data/patterns/survivors.json`
```json
{
  "survivors": [
    { "id": "...", "verdict": "kept", "reasoning": "...", "decision_impact": "..." }
  ],
  "killed": [
    { "id": "...", "verdict": "killed", "reason": "..." }
  ],
  "summary": "X kept of Y. Dimensions that survived: ..."
}
```

**Anti-patterns:**
- No hedging. No "could be relevant." No "maybe." Every pattern is `kept` or `killed`.
- Do NOT add new patterns.
- Do NOT say "more analysis needed."

---

### 5.3 `pattern-antagonist-loop`

**Purpose:** Orchestrate the full fight end-to-end. Convergent, bounded, produces the target description artifact.

**Frontmatter:**
```yaml
---
name: pattern-antagonist-loop
description: Use after the user has an enriched Closed-Won CSV in data/closed-won/ and wants the full pattern↔antagonist fight run end-to-end. Runs pattern-recognition, then antagonist, then up to 2 more rounds where the pattern agent may defend killed patterns and surface new ones, and the antagonist re-prosecutes. Outputs the surviving pattern set and writes data/target-description.md — the artifact describing the best-fit customer and why.
---
```

**Preconditions:** CSV present in `data/closed-won/`.

**Loop mechanics:**
- **Round 1:** pattern-recognition → candidates.json → antagonist → survivors.json
- **Round 2 (grudge):** pattern-recognition re-runs, seeing kill reasons. One chance to defend the 3 most-defensible kills and surface missed interaction effects. Antagonist re-prosecutes.
- **Round 3 (grudge):** Same as Round 2. Final verdict.
- **Convergence rule:** stop early if a round produces <2 changes vs. previous round.
- **Hard cap at 3 rounds.** Non-configurable. Configurability is where overproduction hides.

**Output contract:** `data/target-description.md`
```markdown
# Best-Fit Customer — [inferred name]
## One-sentence description
## Firmographic signature
## Disqualifiers (patterns that explicitly kill fit)
## Confidence notes (which patterns are strong, which are soft)
## Round log (summary of what died and why — for human audit)
```

The Round log is load-bearing — the human uses it to decide whether to resurrect a killed pattern manually.

**Hand-off message:** *"Target description written to `data/target-description.md`. Review the Round log, then invoke `account-search` when ready."*

**Anti-patterns:**
- Do NOT loop past 3 rounds.
- Do NOT write `scoring/*`.
- Do NOT query external APIs.
- Do NOT edit the raw CSV.

---

### 5.4 `account-search`

**Purpose:** Pull a wide raw account list from GTM databases based on the target description. Remix-able via provider adapters.

**Frontmatter:**
```yaml
---
name: account-search
description: Use after data/target-description.md exists and the user wants to pull a wide raw account list from GTM databases (Apollo, Ocean, Clay, Databar, Exa, FullEnrich, Store Leads). Translates the target description into provider-specific search queries, runs them, writes raw results to data/accounts-raw/. Remix-able — users add their own provider adapters.
---
```

**Preconditions:**
- `data/target-description.md` exists.
- At least one provider configured with API credentials (env vars, documented in README).

**Provider registry:** `.claude/skills/account-search/providers/*.md`. Each provider file defines:
- What the provider is good for
- Filter schema it accepts
- How to translate a target-description block into its filters
- API endpoint / MCP reference
- Rate-limit notes

Users drop in `my-provider.md` and the skill picks it up automatically.

**Behavior:**
- Read `data/target-description.md`.
- Select provider(s) based on available credentials and what the description requires.
- Translate firmographic signature into filters.
- Run queries. Dedupe across providers by domain.
- **Wide, not narrow.** If a query returns <500 results, relax filters and note it in the manifest.

**Output contract:**
- `data/accounts-raw/{provider}-{timestamp}.csv`
- `data/accounts-raw/manifest.json` — query params, result counts, providers used.

**Anti-patterns:**
- Do NOT score, tier, or filter results.
- Do NOT enrich.
- Do NOT dedupe against the user's CRM (that's a separate step the user owns).
- Do NOT call `account-scoring`.

---

### 5.5 `account-scoring`

**Purpose:** Two-mode skill. Generates a scoring algorithm from the target description, or runs the existing algorithm against a raw account list to produce tiers.

**Frontmatter:**
```yaml
---
name: account-scoring
description: Use after data/target-description.md exists and the user wants to generate or run a scoring algorithm that turns the description into tiers (T1/T2/T3/T4). Two modes — (1) generate scoring/rules.py + scoring/rules.md + scoring/weights.yaml from the target description, or (2) run the existing scoring/ against data/accounts-raw/ and write data/accounts-scored/tiered.csv. Human is expected to hand-tweak weights and hard-code rules after generation.
---
```

**Mode selection:**
- If `scoring/rules.py` does not exist (repo ships this way — only `scoring/.gitkeep` is checked in) → Generate mode.
- If `scoring/rules.py` exists and `data/accounts-raw/` has at least one CSV → Run mode.
- If both exist and user hasn't explicitly asked to regenerate, default to Run mode. Never silently overwrite `scoring/*` — regeneration requires explicit user consent.

**Generate mode — output contract:**
- `scoring/rules.py` — pure functions, one-line docstring per function stating which pattern from the target description it implements.
- `scoring/rules.md` — LLM-rule definitions: when to use web research / classification calls.
- `scoring/weights.yaml` — 0–100 weight per rule. **Header comment explicitly flags these as starting hypotheses: "TWEAK THIS."**

**Run mode:**
1. Normalize `data/accounts-raw/*.csv` so columns match the Closed-Won schema (this is the "re-enrich the new list to match" step from slide 11).
2. Apply deterministic rules (`scoring/rules.py`).
3. Apply LLM rules (`scoring/rules.md`) where configured.
4. Compute weighted score per account.
5. Assign tiers per thresholds in `weights.yaml`:
   - T1: top 1% OR hand-picked named accounts (separate input list)
   - T2: top ~10% — SDR outbound focus
   - T3: top ~40% — ads / programmatic
   - T4: remainder above a floor — nurture / watchlist
6. Write `data/accounts-scored/tiered.csv` with score, tier, and top-3-contributing-rules per row. Auditability is required — users must be able to answer "why is this account T1?"

**Sense-check gate (mandatory last step in Run mode):**
- Run the Closed-Won CSV through the same pipeline.
- Compute share of Closed-Won rows that land in T1 or T2.
- Threshold is configurable in `scoring/weights.yaml` (default: 80%).
- If share is below threshold, emit loud warning: *"Your algorithm doesn't recognize your own best customers (only X% of Closed-Won landed in T1/T2, threshold is Y%). Tweak weights.yaml or rules.py before you trust the output."*
- Surface the per-Closed-Won tier breakdown so the user can see exactly which customers were misclassified.
- This directly implements the slide 12 pro tip.

**Anti-patterns:**
- Do NOT silently rewrite `weights.yaml` on re-runs — user owns that file.
- Do NOT skip the sense-check.
- Do NOT emit a single-tier output.
- Do NOT call external APIs without declaring it in `scoring/rules.md`.

## 6. README

Front door for attendees. Voice matches the talk — direct, opinionated, no corporate throat-clearing.

**Sections:**
1. One-line pitch + fork instruction.
2. Talk attribution + slide/recording links.
3. Thesis (90 seconds) — two flaws, pattern vs. antagonist.
4. What you need before you start (Claude Code, CRM, enrichment tool, API keys).
5. The 7 steps — mirrors the talk, one invocation per step.
6. Directory map.
7. Skills table — skill, purpose, reads, writes.
8. Remixing — adding providers, tweaking scoring, changing antagonist posture.
9. FAQ / gotchas — pre-answers the obvious objections ("antagonist killed a pattern I know matters," "<20% of Closed-Won in T1/T2," etc.).
10. **Ethics / data handling note** — Closed-Won is customer data; sanitize before committing even though `data/` is gitignored.
11. License + attribution.

## 7. Design decisions & rationale

### JSON intermediates between pattern-recognition and antagonist
Makes the loop deterministic, diff-able across re-runs, auditable. Cost: less human-readable. Accepted.

### Kill-by-default antagonist
Softer scoring (1–5 keep-worthiness) degrades into the agreeable mush the talk calls out. Hard binary verdicts force the fight to be real. Users can manually resurrect killed patterns via the Round log.

### 3-round hard cap on the loop
Configurability is where overproduction hides. If a user wants more rounds, they re-invoke the skill. Convergence rule allows early exit.

### Grudge prompt in rounds 2 and 3
The pattern agent sees the antagonist's kill reasons and must defend with new evidence or interaction effects. This is what makes the loop adversarial vs. two agents politely taking turns. Most likely tuning surface after real use.

### `scoring/` owned by the user, not the skill
The skill generates a starting hypothesis and then gets out of the way. `weights.yaml` is the explicit tuning surface. Rules can be hand-coded. This enforces the slide 12 message: *"you are smarter than the LLM."*

### Sense-check gate in `account-scoring`
Directly implements the slide 12 pro tip. Non-optional because skipping it is exactly the failure mode the talk warns about.

### Provider adapter pattern for `account-search`
Remix surface. Attendees use wildly different GTM stacks; a fixed provider set would force forks to diverge immediately. One markdown file per provider keeps the surface simple.

## 8. Success criteria

- A GTM operator who attended the talk can fork the repo, drop in an enriched Closed-Won CSV, and produce `data/target-description.md` with one skill invocation.
- A second invocation produces a wide raw account list.
- A third invocation produces `scoring/*` files they can hand-edit.
- A fourth invocation produces `data/accounts-scored/tiered.csv` with T1–T4.
- The sense-check gate catches broken algorithms before the user acts on them.
- A user adding a new GTM provider does not need to modify any SKILL.md — only drop a new `.md` file in `account-search/providers/`.
- The repo works on a clean `git clone` with no install steps beyond Claude Code itself.

## 9. Non-goals

- Fully automated, fire-and-forget pipeline. The talk explicitly rejects this; the skills enforce manual gates (Round log review, weights tuning, sense-check).
- Hosted service. This is a fork-and-run repo.
- Support for every CRM / enrichment / database provider in existence. The provider adapter pattern lets users add their own; v1 ships with a representative set.

## 10. Implementation notes (not open questions — flagged for the plan)

- The existing `.gitignore` from the initial repo commit does NOT yet exclude `data/*`. Implementation must update `.gitignore` to: `data/**` and `!data/**/.gitkeep`. Same for `scoring/rules.py`, `scoring/rules.md`, `scoring/weights.yaml` if we want user-generated scoring to stay local — though the spec treats `scoring/` as user-owned and checked into their fork, so this is a user-fork decision, not a repo default.
- `data/target-description.md` is shown in the repo layout as a single file (not a directory with `.gitkeep`). It is gitignored along with the rest of `data/`. The path is canonical and known; the skill writes it.
- Example `scoring-algorithm-sample/` under `examples/` IS checked in — it's teaching material, not user data.

## 11. Open questions for implementation phase

- Exact provider set to include in v1. Talk mentions Apollo, Ocean, DiscoLike, Clay, Databar, Exa, FullEnrich, Store Leads — not all have public APIs / MCPs at the same maturity. Implementation phase picks the shippable set.
- Whether to ship an example `closed-won-sample.csv` using a real anonymized dataset or a synthetic one. Synthetic is safer for a public repo; real-looking is more teachable.
- Whether the loop should persist intermediate `candidates.json` / `survivors.json` per round (for auditability) or overwrite (simpler). Recommendation: persist with round suffix.
