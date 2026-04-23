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
├── .claude/skills/                 # the 6 skills
│   ├── data-audit/                 # pre-flight CSV quality check (runs automatically)
│   ├── pattern-recognition/
│   ├── antagonist/
│   │   └── baselines/              # B2B population baselines for base-rate tests
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
| `data-audit` | `data/closed-won/*.csv` | `data/closed-won/.data-audit.json` (severity + findings) |
| `pattern-recognition` | `data/closed-won/*.csv`, audit JSON | `data/patterns/candidates.json` (with Wilson CIs, lift, provenance) |
| `antagonist` | `data/patterns/candidates.json`, baselines JSON | `data/patterns/survivors.json` (kept + killed w/ failed-test + evidence) |
| `pattern-antagonist-loop` | `data/closed-won/*.csv` | `data/patterns/*-r{1,2,3}.json` + `data/target-description.md` |
| `account-search` | `data/target-description.md` | `data/accounts-raw/<provider>-<ts>.csv`, `deduped-<ts>.csv`, `manifest.json` |
| `account-scoring` (generate) | `data/target-description.md`, `data/closed-won/*.csv` | `scoring/rules.py, rules.md, weights.yaml` (empirically calibrated) |
| `account-scoring` (run) | `scoring/*`, `data/accounts-raw/*.csv` | `data/accounts-scored/tiered.csv`, `closed-won-sense-check.csv`, `run-manifest.json` |

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
