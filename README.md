# antagonistic-agent-account-building

Claude Code skills for adversarial pattern discovery in tabular data. Point a pair of skills at a CSV — one surfaces every pattern the data supports, the other kills the ones that don't matter. The survivors are what you act on.

Originally built as a worked example for GTM account-building. The core skills (`business-context`, `data-audit`, `pattern-recognition`, `antagonist`, `pattern-antagonist-loop`) are **industry-agnostic** and work on any tabular data and any decision. The last two skills (`account-search`, `account-scoring`) specialize the output for GTM workflows.

## Requirements

- [Claude Code](https://docs.claude.com/en/docs/claude-code)
- Python 3.10+ with `pandas` (recommended) and `pyyaml` (required for `account-scoring` generate mode)
- A CSV you want to analyze

## Install

```bash
git clone https://github.com/gunsandroazen/antagonistic-agent-account-building
cd antagonistic-agent-account-building
```

The `.claude/skills/` directory is auto-discovered by Claude Code when you run it in this directory.

## Quick start

```bash
# From inside Claude Code, in the repo root:

/skill business-context              # interactive; produces data/business-context.md

# Put your CSV in data/closed-won/ (or anywhere — the skills accept explicit paths).
cp /path/to/your.csv data/closed-won/

/skill pattern-antagonist-loop       # runs audit → discovery → adversarial loop
                                     # writes data/target-description.md
```

Stop there if you're analyzing non-GTM data. If you're building an account list, continue:

```bash
/skill account-search                # wide pull from GTM providers (needs env vars)
/skill account-scoring               # generates scoring/ from target-description +
                                     # calibrated weights against your Closed-Won

# Hand-edit scoring/weights.yaml and scoring/rules.py, then:

/skill account-scoring               # run mode; writes data/accounts-scored/tiered.csv
```

## Skills

Seven skills, split into three layers.

### Layer 1 — Universal (works on any tabular data, any business)

| Skill | Purpose | Reads | Writes |
|---|---|---|---|
| `business-context` | Interview the user; produce the business-context document the antagonist adjudicates against | conversation (interactive) or a brief document | `data/business-context.md` |
| `data-audit` | Pre-flight CSV quality check. Blocks bad inputs before they pollute the loop | a CSV | `data/closed-won/.data-audit.json` |
| `pattern-recognition` | Universal pattern discovery. Ingests any CSV, reads column by column, emits every pattern the data supports with statistical evidence | any CSV | `data/patterns/candidates.json` |
| `antagonist` | Pure relevance adjudicator. Reads candidates + business-context + baselines, kills patterns that fail any of four tests (decision / base-rate / confound / actionability) | `candidates.json`, `business-context.md`, baselines | `data/patterns/survivors.json` |
| `pattern-antagonist-loop` | Orchestrator. Runs business-context → data-audit → 3-round pattern↔antagonist loop with grudge prompts. Emits the final artifact | a CSV (any path) | `data/patterns/*-r{1,2,3}.json`, `data/target-description.md` |

### Layer 2 — GTM specialization (specific to account-building)

| Skill | Purpose | Reads | Writes |
|---|---|---|---|
| `account-search` | Translates target-description into provider-specific filters. Pulls, dedupes, and normalizes a wide raw account list. Providers are markdown files — drop yours into `providers/` | `data/target-description.md` | `data/accounts-raw/<provider>-<ts>.csv`, `deduped-<ts>.csv`, `manifest.json` |
| `account-scoring` | Generates a scoring algorithm (deterministic rules + LLM rules + weights) from target-description. Calibrates starting weights empirically against your Closed-Won. Runs the algorithm against accounts-raw. Mandatory sense-check: the same rules are run against Closed-Won to verify your best customers land in T1/T2 | `target-description.md`, `accounts-raw/*.csv`, `closed-won/*.csv` | `scoring/{rules.py, rules.md, weights.yaml}`, `data/accounts-scored/tiered.csv`, `closed-won-sense-check.csv` |

### Layer 3 — Resources

| Path | Purpose |
|---|---|
| `.claude/skills/antagonist/baselines/b2b-population-baselines.json` | Shipped B2B population frequencies used by the antagonist's base-rate test. Override by placing a `data/baselines.json` for your industry/vertical |
| `.claude/skills/account-search/providers/*.md` | One markdown file per GTM provider. Ships with Apollo, Ocean, Clay, Databar, Exa, FullEnrich, Store Leads. Add your own |
| `examples/` | Synthetic Closed-Won CSV, sample target-description, sample scoring algorithm. For reference only — not wired into the pipeline |

## Directory layout

```
.
├── .claude/skills/
│   ├── business-context/
│   ├── data-audit/
│   ├── pattern-recognition/
│   ├── antagonist/
│   │   └── baselines/                  # shipped B2B defaults; override via data/baselines.json
│   ├── pattern-antagonist-loop/
│   ├── account-search/
│   │   └── providers/                  # one .md per provider, drop yours in
│   └── account-scoring/
├── data/                               # gitignored — your data stays local
│   ├── business-context.md
│   ├── baselines.json                  # optional override
│   ├── closed-won/                     # input CSVs
│   ├── patterns/                       # pattern + survivor JSON per round
│   ├── target-description.md           # loop output
│   ├── accounts-raw/                   # account-search output
│   └── accounts-scored/                # account-scoring output
├── scoring/                            # gitignored in template; commit to your fork
│   ├── rules.py                        # deterministic rules (generated + hand-edited)
│   ├── rules.md                        # LLM-assisted rules
│   └── weights.yaml                    # weights + thresholds
└── examples/                           # reference artifacts
```

## How it works

### 1. Build context

```
/skill business-context
```

Interactive. Asks about your business, customer, decision being informed, actionable downstream tools, known data-collection biases, hard disqualifiers. Produces `data/business-context.md` in the user's own words.

This is the ground truth the antagonist uses for relevance. **Without this, the antagonist cannot adjudicate — it will stop and ask you to build context first.**

### 2. Audit your data

```
/skill data-audit
```

Or omit it — `pattern-antagonist-loop` invokes it automatically. Checks for:
- Duplicate rows / domains
- Mixed encodings, BOMs, malformed rows
- Free-text in columns that should be numeric
- PII exposure
- >50% null rates across the board
- Extreme cardinality problems

Emits severity: `clean`, `warnings`, or `critical`. `critical` blocks downstream execution until resolved.

### 3. Run the loop

```
/skill pattern-antagonist-loop
```

Sequence:

1. **Round 1:** `pattern-recognition` reads your CSV column by column, profiles each column by inferred type (not by name), emits every candidate pattern (typically 150-600). `antagonist` reads the candidates, the business-context, the baselines, and kills everything that fails any of four tests. Typical kill rate: 70-95%.

2. **Round 2 (grudge):** The loop picks the 3 most-defensible kills and re-runs `pattern-recognition` with an explicit grudge prompt — it must either defend those kills with new evidence (interactions, sub-patterns, adjacent dimensions) or concede. Also hunts for interaction effects it missed in Round 1. The antagonist re-prosecutes.

3. **Round 3 (final grudge):** Same structure. Hard cap at 3 rounds.

4. **Convergence rule:** if fewer than 2 patterns change state between rounds, stop early.

5. **Synthesis:** writes `data/target-description.md` in the user's voice (pulled from business-context.md). Includes firmographic signature, disqualifiers, confidence notes, a round log, and a list of killed patterns worth reviewing manually.

Per-round artifacts (`candidates-r{1,2,3}.json`, `survivors-r{1,2,3}.json`) are kept for audit.

### 4. Act on the output

For GTM account-building:

```
/skill account-search          # pulls raw accounts from configured providers
/skill account-scoring         # generate mode → scoring/, run mode → tiered.csv
```

For anything else: `data/target-description.md` is the deliverable. Feed it into your own downstream tools.

## The four relevance tests

The antagonist kills a pattern unless it passes all four. In order of evaluation:

1. **Sample-size gate.** `total_matches < 10` → kill. Patterns on a handful of rows are noise.
2. **Base-rate test.** Lift over population baseline must be ≥ 2.0 (or ≥ 1.5 with CI lower bound above baseline). If no baseline exists for the dimension, stricter raw thresholds apply (`match_rate ≥ 0.40`, `total_matches ≥ 10`, CI lower ≥ 0.30).
3. **Decision test.** The pattern must point to a specific, nameable decision in the downstream workflow. What that means is defined in your `business-context.md`.
4. **Actionability test.** The pattern must be filterable by the tools listed in your `business-context.md`, OR convertible to an LLM classification rule.
5. **Confound test.** If the pattern plausibly reflects how the data was collected (sales-team geography, warm-intro network, pricing gate, partner channel) rather than a feature of the customer, kill unless lift is very high — then keep with a `confounder_flag`.

Every killed pattern is recorded with its `failed_test` and `evidence_at_kill` for audit.

## Forking for a non-GTM use case

The five core skills are industry-agnostic by design. To adapt the repo:

1. Run `/skill business-context` and answer as your actual business (not GTM).
2. If your customer entity isn't a B2B company (consumer, household, government, etc.), replace or augment `.claude/skills/antagonist/baselines/b2b-population-baselines.json` with a `data/baselines.json` reflecting your population.
3. Skip `account-search` and `account-scoring` — those are GTM-specific. `data/target-description.md` is your deliverable.
4. Build your own action skills downstream and add them to `.claude/skills/`.

## Adding a GTM provider

Drop a markdown file in `.claude/skills/account-search/providers/`. See `providers/README.md` for the schema. The `account-search` skill auto-discovers providers — no other code changes needed.

## Tuning scoring

After `account-scoring` generate mode:

- Edit `scoring/weights.yaml` — every rule has its calibrated starting weight and a comment showing the lift it was computed from.
- Edit `scoring/rules.py` — pure deterministic Python, each rule a single function.
- Edit `scoring/rules.md` — LLM-assisted rules, invoked only on top-30% deterministic scorers (cost control).
- Re-run `/skill account-scoring`.

The sense-check gate will block you from shipping an algorithm that misclassifies your own Closed-Won.

## Data handling

`data/` is gitignored. Your CSVs, business-context, patterns, accounts, and scored output never leave your machine via git.

If you fork, **audit your fork's `.gitignore` before pushing** — accidental leaks are easy.

The skills do not send your CSV or business-context to any external service. Pattern-recognition, antagonist, and the loop are fully local. `account-search` sends query parameters (not your data) to whichever GTM providers you've configured. `account-scoring` LLM rules send individual account domains and targeted research queries to Claude when invoked.

## Statistical notes

- Confidence intervals are Wilson score (robust for small samples).
- Interaction patterns compute lift against independence (`P(A∧B) / (P(A)·P(B))`).
- Time-weighted frequencies use exponential decay with `half_life = 365 days` when a date column is detected.
- Categorical patterns below `total_matches = 10` are killed regardless of lift.
- For full statistical methodology, see the SKILL.md files.

## License

MIT — see [LICENSE](./LICENSE).

## Attribution

Built as the companion repo for Elliot Roazen's _Antagonistic Agents in Account Building_ talk (NYC GTM 2026). The talk explains the motivation and the GTM instantiation; this repo is the general-purpose implementation.

[linkedin.com/in/elliotroazen](https://linkedin.com/in/elliotroazen)
