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
