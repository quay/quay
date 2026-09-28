# Stage D detail: the proposal's fixed shape

Write it in this fixed shape. Every section is required; an empty one is a
finding, not an omission to hide.

1. **Evidence table** — one row per run: run URL, job name, date, outcome
   (flake/fail/pass). Plus the Sippy spanning-row line (`current_runs` /
   `current_successes` / `current_flakes` / `current_failures`) and, if
   artifacts were unreachable, the access gap.
2. **Hypothesis** — the mechanism in one paragraph with file and line
   references, then the candidates **explicitly evaluated and REJECTED**, each
   with its rejecting evidence. No rejected alternatives means untested.
3. **Reproduction** — the exact command and the rate (`5/5`, `0/90`), for both
   the CI-like and the forced-reuse run.
4. **Fix sketch** — as a diff, with the alternatives considered and why they
   were not chosen (blast radius, breaking a sibling assertion).
5. **Confidence** — "confident" (small, targeted, mechanism reproduced) or
   "needs a decision" (list the options with tradeoffs and stop).
6. **Backport note** — does `redhat-X.Y` need the same diff? Check, do not
   guess; an empty diff means the identical patch applies.

   ```bash
   git diff origin/master origin/redhat-3.18 -- "$SPEC" web/playwright/fixtures.ts web/playwright.config.ts
   ```
