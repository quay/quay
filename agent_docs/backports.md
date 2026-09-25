# Backporting to `redhat-*` Release Branches

A checklist for carrying a merged `master` change onto the maintained release
branches. Every rule here comes from a real backport chain (PR #7196 and the
five predecessors it turned out to need, 2026-09-20 to 2026-09-23). Where a
current fact is stated, it is dated and names the command that produced it —
re-run the command instead of trusting the date.

For JIRA Target Version/fixVersions rules and the basic `/cherrypick`/`/jira
backport` mechanics, see `agent_docs/workflow.md` (Target Version &
Backporting, Release Branch Model, Backport Process). This document does not
restate them.

## The rule: fidelity

The ported change differs from `master` only where the branch forces it.

- List every omission and every adaptation, with its reason, in the backport
  PR body. An unexplained difference is a defect in the backport.
- Do not simplify, modernise, or fix unrelated things while porting. Note them
  separately.
- A pre-commit hook's reformatting is an adaptation: keep it, and list it.

## 1. Determine the target branches

Never hardcode the range; it rots. Use the sync check and activity check in
`agent_docs/workflow.md` → Release Branch Model.

- The master-synced branch (`git rev-list --left-right --count
  upstream/<branch>...upstream/master` prints `0 0`) already has the change.
  Never target it. On 2026-09-20 that was `redhat-3.19`.
- Treat any branch list you are handed as a claim to verify.
- For a PROJQUAY-titled change, read the root ticket (the one with no
  outward `clones` link; clones inherit fixVersions) and treat its
  fixVersions as the branch list: map `quay-vX.Y.z` to `redhat-X.Y`, drop any
  `.0` entry (master already has the change), and never target the
  master-synced branch either: `jira issue view <KEY> --raw | jq
  -c '{target: [.fields.customfield_10855[]?.name], fix:
  [.fields.fixVersions[].name]}'`. If that list disagrees with the
  sync/activity determination above, or fixVersions is empty, stop for a
  maintainer decision and get Jira corrected before firing the cascade.
  NO-ISSUE changes keep the sync/activity rule above unchanged.
- Check the branch's lifecycle phase (workflow.md → Release Branch Model): a
  Maintenance Support branch takes only a Critical/Important security fix or
  an urgent or selected high-priority bug fix — otherwise drop it, and for a
  PROJQUAY change whose fixVersions names it, get a maintainer call.

## 2. Survey for missing predecessors before firing anything

Run this over the commit's **own** path set, once per target branch. Do not
wait for a conflict, and do not scope it to conflicting files: #7196 was
missing five predecessors, and a conflict-scoped survey found one.

```bash
git fetch upstream --prune
PATHS=$(git diff-tree --no-commit-id --name-only -r <master-sha>^1 <master-sha>)
git log --oneline --cherry-pick --right-only --no-merges \
    upstream/<branch>...upstream/master -- $PATHS
```

`--cherry-pick` hides commits already ported under a different sha. Then clear
the false positives by hand before calling anything missing:

- **Re-authored backports.** A fix rewritten on the branch instead of
  cherry-picked has a different patch-id and still shows up. Check the path's
  own branch log for a `[redhat-X.Y]` counterpart. (#7235 is on the branches as
  #7253/#7254/#7255.)
- **Commits newer than the one you are porting** are not predecessors
  (`git merge-base --is-ancestor <candidate> <master-sha>`).

Never verify a backport by Jira key. One key can cover two PRs: on
2026-09-20, `git log upstream/redhat-3.18 --grep=PROJQUAY-8272` found #3427
and read as "backported", while #6892 under the same key was missing from
3.18, 3.17 and 3.16. Keys also change across a backport (master #6511 is PROJQUAY-12223, its
3.18 port PROJQUAY-13331). Verify by sha, by subject, or by the hunk in the
file.

Classify each survivor, per branch — a branch can lack something a newer
branch has:

| Finding | Action |
| --- | --- |
| Missed backport the change depends on | Report it. Port it first (step 4). |
| Missed backport that is only a neighbour | Port your own hunks, state the neighbour as unported. |
| Deliberate divergence (a feature the branch never got) | State it; see step 5. |

**Adjacency is not dependency.** A 3-way merge bundles hunks by line
proximity. Decide dependency from your own diff: does a hunk call, import or
build on something only the missing commit introduces? #6511 on 3.17 conflicted
next to #5403's tests; nothing in #6511 needed #5403, so #6511's hunks went in
alone and #5403 was reported as unported.

**A file's absence proves nothing about why.** `nested-index.spec.ts` was
recorded as "deleted in 3.18"; `git log --diff-filter=AD upstream/master --
<path>` showed #6892 created it and was never backported. Deleted-on-purpose
and never-backported look the same in a conflict and need opposite fixes.

Report the ordered chain before the first hop command. What to do about a
missing predecessor is the maintainer's call; never absorb it silently into
another change's backport.

## 3. Bot first, as a cascade

The cascade runs newest branch to oldest, each step picked from the previous
branch's **merged** PR, one branch per comment. For a PROJQUAY-titled PR,
fire `/jira backport <branch>`; for a NO-ISSUE or QUAYIO-titled PR, fire
`/cherrypick <branch>`. To skip over an intermediate branch, `/jira backport`
a comma-separated list naming every branch from the current PR down to the
target — this also clones the skipped branch's ticket, which a human then
sets to Won't Do. `/cherrypick` has no such form: skip a branch by firing
`/cherrypick <target>` alone on the last merged PR (see the multi-branch
caveat below):

1. `/jira backport redhat-3.18` on the master PR.
2. After that PR merges: `/jira backport redhat-3.17` on the 3.18 PR.
3. After that PR merges: `/jira backport redhat-3.16` on the 3.17 PR.

(Branch names as of 2026-09-20; determine yours with step 1. `redhat-3.16` is
Maintenance Support — port to it only if the change qualifies, per step 1.)

- One branch per comment. A multi-branch comment chains automatically, but a
  failure comment lands on the intermediate PR it opened, not the one you
  commented on, and later branches are silently never tried (#6511:
  `/cherrypick redhat-3.18 redhat-3.17 redhat-3.16` on the master PR opened
  #7266 for 3.18 and carried `redhat-3.17 redhat-3.16` into its body; when
  #7266 merged, the bot tried 3.17 from #7266 and posted the failure there,
  and 3.16 was never tried).
- Check the PR's existing comments before firing, so a chain is never started
  twice.
- Picking from the previous branch reuses its adaptations. Firing an older
  branch from `master` skips them and manufactures conflicts.
- After a `/jira backport`, read the bot's "The following backport issues
  have been created" reply; an empty list means no clone was made.

Bot-first is also a scheduling rule. A bot-authored PR can be approved by any
approver; a hand-written one needs an approving review from someone who is not
its author. On this chain that was from 30 minutes to 14 hours per manual PR,
and a long-open manual port can go stale when the branch moves under it (#7269
was superseded by #7276, the same change rebased, after #7272 merged
beneath it).

Before treating a bot comment as terminal, check what actually happened.
`Ignoring requests to cherry-pick non-bug issues` comes from the Jira
lifecycle plugin declining to clone the Jira issue; the cherry-pick robot
still opened the PR (#7330, #7336). Check for the branch PR itself, and
compare its `createdAt` with the time you looked.

## 4. When the bot fails

A conflict is evidence. Reproduce it read-only first:

```bash
git merge-tree --write-tree --merge-base=<master-sha>^ upstream/<branch> <master-sha>
```

Use the commit's **parent** as the merge base. The branch-point
(`git merge-base`) form merges all of master's divergence and reports dozens of
unrelated conflicts.

Then, in order:

1. If a missing predecessor explains the conflict, land the predecessor (by the
   bot, where it applies) and **re-fire the bot**. #6612 on 3.17 failed on a
   missing test file; landing that file first (#7280) let the re-fire apply
   cleanly, and the whole item stayed bot-authored.
2. Hand-port only when the bot fails again, or no predecessor explains it.
   Port to the newest failing branch first, get it reviewed and merged, and
   continue the cascade from that merged PR. Title a PROJQUAY hand-port
   `[redhat-X.Y] PROJQUAY-<clone>: ...` using the clone key from the
   `/jira backport` reply, never the master key: #7319 retitled from the
   master key to PROJQUAY-13339, which then moved to MODIFIED on merge, while
   the master-key hand-ports #7268/#7276/#7310 got "unrecognized state
   (MODIFIED)". After opening the hand-port PR, comment `/jira refresh` to
   link the clone ticket and validate its Target Version.
3. Land predecessors in `master` merge order, oldest first.

If `git rerere` is enabled, a conflict you resolved on an earlier branch is
replayed silently: no markers, `git status` still shows `UU`, and only a
`Resolved '<path>' using previous resolution.` line on stderr. Review a replay
as carefully as a hand resolution; `git checkout --merge -- <path>` restores
the markers.

## 5. What to port, and what to drop

| Change | Default |
| --- | --- |
| Product fix for a defect the branch has | Port |
| Test/CI machinery the branch's own CI or periodics need | Port |
| Test fix keeping the branch's suite green | Port |
| New feature or behaviour change | Ask first |
| Refactor with no defect behind it | Ask first; only as a predecessor |
| Fix for code the branch does not have | Skip, and state it |

- A fix for an absent feature is moot, not missing: #6750 fixes bootstrap token
  renewal (#6350), which 3.17 and 3.16 never received, so it was skipped there
  and said so. Porting the whole feature to make a fix apply is a separate
  decision.
- A test travels with the product change it covers. A test for a feature the
  branch lacks is dropped and stated, naming the PR that would bring the
  feature.
- Where the branch's own code has diverged, keep both the branch's additions
  and what you port. Do not delete branch-local code to make a hunk apply.
- **The line:** if you find yourself reconstructing behaviour from an unported
  change to make a hunk apply, stop and ask.

## 6. Verify, per branch

- The ported files lint and typecheck to the standard the branch already holds.
- Install the branch's own pinned dependencies to run its Python tests; a venv
  built for another branch fails in ways that look like the change's fault.
- The ported machinery is **present and wired**, not just applied — check the
  call sites. #7196's point was `web/playwright/utils/failure-artifacts.ts` and
  its import in `web/playwright/fixtures.ts`; a clean apply proves neither.
- Read your port's diff against master's original diff, hunk by hunk. Every
  difference is either listed with a reason or is a defect.
- If a check needs CI or a live stack you do not have, say so; the backport
  PR's CI run is where it is first observed. #7196 on 3.16 needed a Jaeger
  config key the branch reads differently (`OTEL_TRACES_SAMPLER_ARG`, not 3.17's
  `sample_rate`); a verbatim copy would have parsed and exported almost no
  spans.

## 7. The PR body

- Bot PRs carry the bot's body. For a hand port, state: the master PR, the
  branch PR it cascaded from, every conflict and how it was resolved, every
  omission and adaptation with its reason, and what could and could not be
  verified.
- In a chain status, say which PRs were bot-authored and which were manual; the
  two merge on very different timescales.
- Title the PR per step 4's hand-port rule above.
