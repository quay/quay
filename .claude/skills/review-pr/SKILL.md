---
name: review-pr
description: Run a three-reviewer peer review on a GitHub pull request, then synthesize the findings into one evidence-backed review. Use for PR numbers or PR URLs.
argument-hint: [pr-number-or-url]
disable-model-invocation: true
model: claude-opus-4-6
---

# Multi-Agent PR Review

Review the pull request identified by `$ARGUMENTS` using a three-reviewer peer
review workflow. Do not edit code, push commits, or post GitHub comments unless
the user explicitly asks.

## Required workflow

1. Parse `$ARGUMENTS` as either a PR number or a GitHub PR URL.
2. Do only the minimum parent-side setup needed to compose the reviewer prompt.
   - identify the PR
   - fetch the PR metadata and diff surface once if needed
   - do not perform deep review or serial model-specific analysis yourself yet
3. Launch these three subagents in parallel and keep them independent.
   - In Cursor, use:
     - `pr-review-gemini-3-1-pro`
     - `pr-review-gpt-5-4-high`
     - `pr-review-claude-4-6-opus-high-thinking`
   - In Claude Code, use:
     - `pr-review-haiku`
     - `pr-review-sonnet`
     - `pr-review-opus`
4. Issue all three subagent launches in the same message/tool batch.
   - Do not launch reviewer 1, wait, then reviewer 2, then reviewer 3.
   - Do not do additional parent analysis between the three launches.
   - The launch is only considered parallel if all three subagent `started`
     events occur before the first reviewer completes.
5. Give each subagent the same assignment:
   - Review only the changes in the target PR.
   - Gather evidence using `gh pr view`, `gh pr diff`, `gh pr checks`, and
     direct code inspection.
   - Focus findings on bugs, regressions, performance/scaling risks, security
     issues, migration hazards, and missing tests.
   - Avoid style-only comments unless they hide a real defect.
   - Return findings, review perspective, open questions, test gaps, and a
     verdict.
6. Wait for all reviewers to finish before writing the final answer.
7. Synthesize the outputs yourself using the same model family as
   `pr-review-opus`.

## Synthesis rules

- Deduplicate overlapping findings.
- Record consensus as `1/3`, `2/3`, or `3/3`.
- Prefer evidence over vote count. A strong minority finding can stay if you
  verify it directly.
- If reviewers disagree, inspect the code yourself before deciding.
- Keep the final review focused on bugs, risks, behavioral regressions, and
  missing tests.
- State explicitly when confidence is reduced because a subagent could not run.
- Add a reviewer-comparison summary that explains what each reviewer emphasized,
  where they disagreed, and whether the multi-agent run added material value
  over a single strong review.
- If the reviewers were not launched in a single batch, say that the run used
  degraded concurrency.

## Final output format

Use this structure:

## Findings
- One bullet per finding, ordered by severity.
- Include: severity, consensus count, impacted paths, why it matters, and a
  concrete fix direction.
- If there are no findings, say that explicitly.

## Open Questions
- Clarifications or assumptions that affect confidence.

## Reviewer Comparison
- Compare what each reviewer emphasized and whether any model surfaced unique
  evidence-backed findings.

## Incremental Value
- State whether the multi-agent review materially improved the result.
- Note any unique findings or disagreements that changed the final assessment.
- State whether a single strong reviewer likely would have been sufficient for
  this PR.
- State whether the reviewers actually ran in parallel or in degraded
  sequential/staggered mode.

## Testing Gaps
- Important missing tests or verification steps.

## Summary
- A short overall assessment and verdict.

## Cursor note

Cursor has a dedicated override at `.cursor/skills/review-pr/SKILL.md` and
Cursor-specific agent definitions in `.cursor/agents/`. Claude Code uses the
definitions in `.claude/agents/`.
