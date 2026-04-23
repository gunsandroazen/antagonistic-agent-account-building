---
name: pattern-antagonist-loop
description: Use when the user has an enriched Closed-Won CSV in data/closed-won/ and wants the full pattern↔antagonist fight run end-to-end. Orchestrates data-audit → pattern-recognition → antagonist for up to 3 rounds with explicit grudge prompts that force the pattern agent to defend kills and surface interactions it missed. Detects convergence, writes per-round artifacts, synthesizes the final target-description.md with full round log, and supports per-segment runs when the CSV has a segment column. Deterministic orchestration — no agreeable shortcuts.
---

# Pattern-Antagonist Loop Skill

## Your role

Orchestrate the fight. Run up to 3 rounds. Force real adversarial pressure in rounds 2 and 3. Converge early when further rounds won't find more signal. Synthesize a target-description.md that a GTM operator can audit, not just accept.

You are a conductor, not a player — this skill drives the other skills but does not itself analyze patterns or prosecute them.

---

## Preconditions

1. `data/closed-won/` contains exactly one `.csv` file. If zero, STOP. If multiple, tell the user to pick one.
2. `data/closed-won/.data-audit.json` exists AND has `severity != "critical"`. If it doesn't exist, invoke the `data-audit` skill first. If critical, STOP and surface the blockers.
3. `.claude/skills/antagonist/baselines/b2b-population-baselines.json` exists (shipped with the repo).

---

## Orchestration sequence

### Stage 0 — Audit

If `.data-audit.json` is missing, invoke `data-audit`. If `severity == "critical"` after audit, STOP and print the blockers. If `severity == "warnings"`, proceed but echo the warnings to the user once at the start.

### Stage 1 — Segmentation decision

Read the CSV header. If any column name matches `/^(segment|offering|product_line|customer_type|tier|plan|vertical)$/i`, and that column has 2-6 distinct non-null values, ASK the user:

```
Detected possible segment column: '<col_name>' with values <list>.
Run the loop once overall (one target description) or once per segment (N descriptions)?
[o]verall / [s]egmented / [c]ancel
```

Default to overall if the column has >6 values or is >30% null. If the user is not interactive (e.g., running non-interactively via the CLI), default to overall AND write a note at the top of `target-description.md` recommending a segmented re-run.

For segmented runs, repeat Stages 2-4 once per segment, writing to `data/patterns/<segment-slug>/` and producing `data/target-description.<segment-slug>.md`. Also produce `data/target-description.md` that indexes them.

### Stage 2 — Round 1

1. Invoke `pattern-recognition`. It writes `data/patterns/candidates.json`.
2. Rename that file to `data/patterns/candidates-r1.json`.
3. Invoke `antagonist`. It writes `data/patterns/survivors.json`.
4. Rename to `data/patterns/survivors-r1.json`.
5. Log: `Round 1 complete. N candidates, K kept, M killed.`

### Stage 3 — Round 2 (grudge round)

This round is NOT a re-run of pattern-recognition with the same inputs. It is a focused re-run with explicit antagonistic framing.

1. Load `survivors-r1.json`.
2. From the `killed` array, pick the **3 patterns with the strongest raw evidence (highest match_rate × total_matches)**. These are the "most defensible kills" — patterns the antagonist killed despite having large raw support.
3. Invoke `pattern-recognition` with this explicit grudge prompt appended to its normal instructions:

   ```
   GRUDGE ROUND. The antagonist killed the following 3 patterns in Round 1. For each, you must either:
     a) Defend it with new evidence the antagonist missed — a better base-rate comparison, a narrower sub-pattern with higher lift, or an interaction that changes the calculus.
     b) Concede the kill and say why.

   Additionally, hunt for INTERACTION effects you didn't emit in Round 1. Specifically, look at every pair of Round-1 SURVIVORS and compute joint match rate + lift. Emit the interactions with lift >= 2.0 as new candidate patterns.

   Kills to reconsider:
     <pattern_id_1>: killed because <failed_test>, reason <reason>, evidence <match_rate> / <total_matches>
     <pattern_id_2>: ...
     <pattern_id_3>: ...

   Round-1 survivors (for interaction hunting):
     <list of survivor ids with their dimensions>

   Write output to data/patterns/candidates-r2.json.
   This file must include:
     - All Round-1 survivors (unchanged, pass-through)
     - Your defenses or concessions of the 3 kills (as new or re-evidenced pattern entries)
     - Any new interaction patterns
     - A top-level `grudge_context` block listing which kills you defended vs conceded.
   ```

4. Invoke `antagonist` against `candidates-r2.json`. Writes `survivors-r2.json`.
5. Log: `Round 2 complete. N candidates (K carried, G defended, I new interactions). Final: K' kept, M' killed.`

### Stage 4 — Convergence check

Compare `survivors-r2.json` to `survivors-r1.json`:
- Compute `delta` = number of patterns that changed state (kept→killed OR killed→kept OR newly introduced and kept).
- If `delta < 2`, **converge early** — use `survivors-r2.json` as final. Skip Round 3.
- If `delta >= 2`, proceed to Round 3.

### Stage 5 — Round 3 (if not converged)

Same structure as Round 2, operating on `survivors-r2.json` instead of `r1`. Writes `candidates-r3.json` and `survivors-r3.json`.

**Hard cap at 3 rounds regardless.** If the user wants more rounds, they re-invoke this skill.

### Stage 6 — Synthesize target description

Load the final `survivors-rN.json` (whichever round was last).

Group survivors by dimension family. For each family, pick the single strongest pattern (highest `lift`) as the canonical expression; list related survivors underneath. This prevents the target-description from being a flat dump of 20 barely-different headcount bands.

Dimension families (collapse to one representative):
- Location: HQ country, state, region, metro, city — pick narrowest with lift ≥ 2.0.
- Size: headcount, revenue, funding total — pick each independently if they add info.
- Maturity: funding stage, company age, ownership type.
- Tech stack: individual tools + interaction patterns — list individually; tech stack is high-info.
- Industry: broad industry, subcategory.
- Disqualifiers: all negative patterns — list individually.

Write `data/target-description.md` with this exact structure:

```markdown
# Best-Fit Customer

_Generated from <source_csv> · <row_count> Closed-Won rows · <N> surviving patterns · <R> rounds_

## One-sentence description

[A synthesized sentence describing the best-fit customer. Must be specific: who they are, what they do, why they fit. Should mention 2-3 of the strongest dimensions. Written in active voice.]

## Firmographic signature

[Organized by dimension family. Each bullet cites lift where meaningful.]

**Location**
- HQ in [region/metro], concentrated in [top cities]. (lift: <x>)

**Size**
- Headcount: [band]. (lift: <x>)
- Revenue: [band if surfaced]. (lift: <x>)

**Maturity**
- [funding stage] through [funding stage]. (lift: <x>)
- Private; [age band] year-old companies. (lift: <x>)

**Tech stack signal**
- [tool 1] present in <X%> of Closed-Won. (lift: <y> vs population)
- [interaction] pattern — lift: <z>.

**Industry**
- [broad industry / subcategory]. (lift: <x>)

## Disqualifiers

_Patterns that explicitly kill fit when present. These become negative-weight rules at scoring time._
- [pattern] — <reasoning>.
- ...

## Confidence notes

**Strong signal** (survived all rounds with lift >= 3.0):
- <pattern>: lift <x>, <match_rate>% of Closed-Won. <one-sentence why it's load-bearing>.

**Soft signal** (passed tests but with caveats):
- <pattern>: <caveat — e.g., confounder_flag: possible_selection_bias>.

**Known unknowns** (dimensions the data didn't cover well):
- <dimension>: <why we can't conclude — e.g., 52% null rate, sample too sparse after filtering>.
- Baselines missing for: <list from antagonist's baselines_missing_for_dimensions>.

## Round log

| Round | Candidates | Kept | Killed | Key movements |
|-------|-----------|------|--------|---------------|
| 1 | <N1> | <K1> | <M1> | — |
| 2 | <N2> | <K2> | <M2> | Defended: <p1>, <p2>. New interactions: <i1>, <i2>. |
| 3 | <N3> | <K3> | <M3> | <either "Converged (delta=0)" or key movements> |

**Killed patterns worth reviewing manually:**
_(patterns where the kill felt close — lift 1.3-1.7, or sample size was the only failure)_
- `<id>`: killed because <reason>. If you have reason to believe this matters (e.g., you've seen it in your pipeline), uncomment the corresponding rule in `scoring/rules.py` after running `account-scoring` in generate mode.
- ...

## Provenance

- Source CSV: `<path>` (`<row_count>` rows)
- Candidates per round: `data/patterns/candidates-r{1,2,3}.json`
- Survivors per round: `data/patterns/survivors-r{1,2,3}.json`
- Baselines used: `.claude/skills/antagonist/baselines/b2b-population-baselines.json`
- Generated: `<ISO-8601 timestamp>`

---

_Next: `/skill account-search` to pull a wide raw account list based on this description._
```

Do not skip any section. If a section would be empty (e.g., no disqualifiers survived), write *"(none — antagonist did not surface any pattern that met the disqualifier bar)"* explicitly.

---

## Anti-patterns

- Do NOT run more than 3 rounds.
- Do NOT write `scoring/*` files.
- Do NOT call external APIs.
- Do NOT edit the raw CSV.
- Do NOT skip writing target-description.md even if few patterns survived.
- Do NOT shortcut the grudge round by just re-running pattern-recognition with the same inputs. The grudge prompt is the whole point — if it's skipped, you have not run this skill.

---

## Hand-off

After writing `target-description.md`, print to user:

```
Loop complete (<R> rounds, <delta> changes in final round).
  Round 1: <N1> candidates → <K1> kept / <M1> killed
  Round 2: <N2> candidates → <K2> kept / <M2> killed
  Round 3: <either stats or "skipped — converged">
  Final survivors: <K>

Strong signals: <top 3 patterns by lift>
Disqualifiers surfaced: <count>
Killed patterns worth manual review: <count>

Target description: data/target-description.md
Per-round artifacts: data/patterns/*-r{1,2,3}.json

Next: `/skill account-search` to pull a raw account list.
```
