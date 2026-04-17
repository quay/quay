#!/bin/bash
# poll-pr.sh -- Stateful PR poller: GitHub Actions CI, CodeRabbit, Codecov, human reviews.
#
# Usage: bash .claude/scripts/poll-pr.sh <PR_NUMBER> [OPTIONS]
#
# Options:
#   --repo OWNER/REPO        Repository (default: quay/quay)
#   --once                   Single poll; exit immediately (default: loop until done)
#   --full                   Always print full report (default: delta-only on re-polls)
#   --max-polls N            Stop after N total polls (default: unlimited)
#
# Exit codes:
#   0  All checks pass — ready to merge
#   1  CI failures — fix required
#   2  Checks still pending — re-poll later
#   3  Review comments to address
#   4  Awaiting human review — posts @quay/downstream mention and exits
#
# State file: .claude/poll-state/pr-<NUMBER>.json
#   Tracks check states, review states, comment counts, adaptive sleep, and poll history.

set -euo pipefail

PR_NUMBER="${1:?Usage: poll-pr.sh <PR_NUMBER> [--repo OWNER/REPO] [--once] [--full] [--max-polls N]}"
if ! [[ "$PR_NUMBER" =~ ^[0-9]+$ ]]; then
  echo "PR_NUMBER must be a positive integer: ${PR_NUMBER}" >&2; exit 1
fi
shift

REPO="quay/quay"
ONCE=false
FULL=false
MAX_POLLS=0  # 0 = unlimited
while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      [ $# -lt 2 ] && { echo "Missing value for --repo" >&2; exit 1; }
      [[ "$2" == -* ]] && { echo "Invalid value for --repo: $2" >&2; exit 1; }
      REPO="$2"; shift 2 ;;
    --once)       ONCE=true; shift ;;
    --full)       FULL=true; shift ;;
    --max-polls)
      [ $# -lt 2 ] && { echo "Missing value for --max-polls" >&2; exit 1; }
      [[ "$2" =~ ^[0-9]+$ ]] || { echo "Invalid value for --max-polls: $2" >&2; exit 1; }
      MAX_POLLS="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

# ── State file setup ─────────────────────────────────────────────────────────
STATE_DIR=".claude/poll-state"
STATE_FILE="${STATE_DIR}/pr-${PR_NUMBER}.json"
mkdir -p "$STATE_DIR"

# ── Helpers ──────────────────────────────────────────────────────────────────

load_state() {
  if [ -f "$STATE_FILE" ]; then cat "$STATE_FILE"; else echo '{}'; fi
}

# Safe jq string read with fallback (normalises JSON null to the fallback value)
jq_str() {
  local _v
  _v=$(echo "$1" | jq -r "${2}" 2>/dev/null) || { echo "${3:-}"; return; }
  [ "$_v" = "null" ] && _v="${3:-}"
  echo "$_v"
}

# Safe jq numeric read with fallback (treats jq errors AND literal "null" as missing)
jq_int() {
  local _v
  _v=$(echo "$1" | jq "${2}" 2>/dev/null) || { echo "${3:-0}"; return; }
  [ "$_v" = "null" ] && _v="${3:-0}"
  echo "$_v"
}

# Compute adaptive sleep based on pending checks and stability of state
adaptive_sleep() {
  local pending="$1" unchanged="$2" prev_sleep="$3"
  if [ "$pending" -eq 0 ]; then
    echo 0       # Nothing pending — don't sleep, something is actionable
  elif [ "$unchanged" -ge 2 ]; then
    local base=$prev_sleep
    [ "$base" -lt 120 ] && base=120
    local next=$(( base * 2 ))
    [ "$next" -gt 600 ] && next=600
    echo "$next" # Backing off: nothing changed across multiple polls
  elif [ "$pending" -gt 3 ]; then
    echo 180     # Many checks pending — jobs likely just queued
  else
    echo 120     # A few checks pending — jobs running
  fi
}

# Post a "ready for review" comment mentioning @quay/downstream (idempotent: checks GitHub API)
notify_for_review() {
  local summary="$1"
  echo "  Posting ready-for-review comment..."

  # Idempotency: check GitHub API for an existing ready-for-review comment regardless of state file
  # Treat API failures as "skip posting" to avoid duplicate comments on transient errors
  local existing_id api_ok=true
  existing_id=$(gh api --paginate "repos/${REPO}/issues/${PR_NUMBER}/comments" \
    --jq '[.[] | select(.body | startswith("## Ready for Review"))] | .[-1].id // empty' \
    2>/dev/null) || api_ok=false
  if ! $api_ok; then
    echo "  WARN: could not verify existing ready-for-review comment; will retry next poll."
    return 1
  fi

  # Post PR comment if not already present — use printf so \n expands to real newlines
  if [ -z "$existing_id" ]; then
    local body
    body=$(printf '## Ready for Review\n\nCI is green and all review threads are resolved.\n\n%s' "$summary")
    gh api "repos/${REPO}/issues/${PR_NUMBER}/comments" \
      -X POST -f body="$body" > /dev/null 2>&1 || return 1
  else
    echo "  Ready-for-review comment already posted (id: ${existing_id})."
  fi

  # Assign quay/downstream team as reviewer via API (best-effort — team may not be a collaborator)
  gh api "repos/${REPO}/pulls/${PR_NUMBER}/requested_reviewers" \
    -X POST -f "team_reviewers[]=downstream" > /dev/null 2>&1 || \
    echo "  NOTE: quay/downstream team assignment skipped (not a repo collaborator)."
}

# Fetch all CodeRabbit review threads via GraphQL (includes resolved/outdated status)
fetch_review_threads() {
  local owner="${REPO%%/*}" rname="${REPO##*/}"
  local result
  result=$(gh api graphql \
    -f query='query($owner:String!,$repo:String!,$pr:Int!){
      repository(owner:$owner,name:$repo){pullRequest(number:$pr){reviewThreads(first:100){
        pageInfo{hasNextPage}
        nodes{
          id isResolved isOutdated
          comments(first:3){nodes{databaseId author{login __typename} body path line originalLine}}
        }
      }}}}'  \
    -f owner="$owner" -f repo="$rname" -F pr="$PR_NUMBER" 2>/dev/null) || return 1
  local has_next
  has_next=$(echo "$result" | jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.hasNextPage // false' 2>/dev/null)
  if [ "$has_next" = "true" ]; then
    echo "  WARN: PR has >100 review threads; results are truncated — counts may be understated." >&2
  fi
  echo "$result"
}

# ── Core poll ────────────────────────────────────────────────────────────────

do_poll() {
  local now now_display
  now=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
  now_display=$(date '+%Y-%m-%d %H:%M:%S')

  local prev
  prev=$(load_state)

  local is_first=false
  [ "$prev" = '{}' ] && is_first=true

  local prev_count prev_sleep prev_unchanged first_polled_at
  prev_count=$(jq_int "$prev" '.poll_count // 0')
  prev_sleep=$(jq_int "$prev" '.next_sleep_seconds // 120')
  prev_unchanged=$(jq_int "$prev" '.consecutive_unchanged_polls // 0')
  first_polled_at=$(jq_str "$prev" '.first_polled_at' "$now")
  local prev_review_notified_at
  prev_review_notified_at=$(jq_str "$prev" '.review_notified_at' '')
  $is_first && first_polled_at="$now"

  local poll_num=$(( prev_count + 1 ))

  # ── Fetch from GitHub ───────────────────────────────────────────────────
  local pr_meta checks_json cr_review cr_inline_count human_inline_count walkthrough_body codecov_body human_reviews_json jira_body

  local head_sha
  head_sha=$(gh pr view "$PR_NUMBER" --repo "$REPO" \
    --json headRefOid --jq '.headRefOid' 2>/dev/null || echo '')

  pr_meta=$(gh pr view "$PR_NUMBER" --repo "$REPO" \
    --json title,state,isDraft,mergeable,labels,reviewDecision \
    --jq '{title,state,draft:.isDraft,mergeable,
           review_decision:.reviewDecision,
           labels:([.labels[].name]|join(","))}' \
    2>/dev/null || echo '{}')

  local checks_rc=0
  checks_json=$(gh pr checks "$PR_NUMBER" --repo "$REPO" --json name,state,bucket \
    2>/dev/null) || checks_rc=$?
  # gh pr checks exits non-zero for pending (8) and failure (1) — not API errors.
  # Keep the JSON for known check-state exits; only fall back on true command failure.
  if [ "$checks_rc" -ne 0 ] && [ "$checks_rc" -ne 1 ] && [ "$checks_rc" -ne 8 ]; then
    echo "  WARN: failed to fetch PR checks (rc=${checks_rc}); treating as pending." >&2
    checks_json='[{"name":"gh pr checks","state":"PENDING","bucket":"pending"}]'
  elif [ -z "$checks_json" ] && [ "$checks_rc" -ne 0 ]; then
    echo "  WARN: gh pr checks returned rc=${checks_rc} with no output; treating as pending." >&2
    checks_json='[{"name":"gh pr checks","state":"PENDING","bucket":"pending"}]'
  elif [ -z "$checks_json" ]; then
    checks_json='[]'
  fi

  cr_review=$(gh api --paginate "repos/${REPO}/pulls/${PR_NUMBER}/reviews" \
    --jq '[.[] | select(.user.login == "coderabbitai[bot]")]' \
    2>/dev/null | jq -s 'flatten | last // {}' || echo '{}')

  local threads_json threads_ok=true
  threads_json=$(fetch_review_threads) || { threads_ok=false; threads_json='{}'; echo "  WARN: GraphQL review-thread fetch failed; treating as indeterminate." >&2; }
  cr_inline_count=$(echo "$threads_json" | jq \
    '[.data.repository.pullRequest.reviewThreads.nodes[]? |
      select(.isResolved==false and .isOutdated==false) |
      select(.comments.nodes[0]?.author.__typename=="Bot" and (.comments.nodes[0]?.author.login | startswith("coderabbit")))] | length' \
    2>/dev/null || echo '0')

  human_inline_count=$(echo "$threads_json" | jq \
    '[.data.repository.pullRequest.reviewThreads.nodes[]? |
      select(.isResolved==false and .isOutdated==false) |
      select(.comments.nodes[0]?.author.__typename=="User")] | length' \
    2>/dev/null || echo '0')

  walkthrough_body=$(gh api --paginate "repos/${REPO}/issues/${PR_NUMBER}/comments" \
    --jq '[.[] | select(.user.login == "coderabbitai[bot]")]' \
    2>/dev/null | jq -rs 'flatten | last | .body // ""' || echo '')

  codecov_body=$(gh api --paginate "repos/${REPO}/issues/${PR_NUMBER}/comments" \
    --jq '[.[] | select(.user.login == "codecov[bot]")]' \
    2>/dev/null | jq -rs 'flatten | last | .body // ""' || echo '')

  human_reviews_json=$(gh api --paginate "repos/${REPO}/pulls/${PR_NUMBER}/reviews" \
    --jq '[.[] | select(.user.login != "coderabbitai[bot]" and .user.login != "github-actions[bot]")]' \
    2>/dev/null | jq -s 'flatten | map({(.user.login): .state}) | add // {}' || echo '{}')

  jira_body=$(gh api --paginate "repos/${REPO}/issues/${PR_NUMBER}/comments" \
    --jq '[.[] | select(.user.login == "openshift-ci[bot]" or .user.login == "openshift-ci-robot")]' \
    2>/dev/null | jq -rs 'flatten | last | .body // ""' || echo '')

  # Human PR comments (non-bot, non-our-own-account)
  # Note: gh api does not support --arg for jq variables; filter in a separate jq call
  local human_comments_json self_login _comments_raw
  self_login=$(gh api user --jq '.login' 2>/dev/null || echo '')
  if _comments_raw=$(gh api --paginate "repos/${REPO}/issues/${PR_NUMBER}/comments" 2>/dev/null); then
    human_comments_json=$(printf '%s' "$_comments_raw" | jq -s --arg self "$self_login" \
      'flatten | [.[] | select(
        (.user.login | endswith("[bot]") | not) and
        .user.login != "openshift-ci-robot" and
        ($self == "" or .user.login != $self) and
        (.body | startswith("## Ready for Review") | not)
      ) | {id: .id, login: .user.login, created_at: .created_at, body: .body}] | sort_by(.id)' \
      2>/dev/null) || human_comments_json='[]'
  else
    human_comments_json='[]'
  fi
  local human_comment_count human_comment_last_id
  human_comment_count=$(echo "$human_comments_json" | jq 'length')
  human_comment_last_id=$(echo "$human_comments_json" | jq '.[-1].id // 0')

  # ── Compute check summary ───────────────────────────────────────────────
  local total pass fail pending
  total=$(jq_int "$checks_json" 'length')
  pass=$(jq_int "$checks_json" '[.[] | select(.bucket == "pass")] | length')
  fail=$(jq_int "$checks_json" '[.[] | select(.bucket == "fail" or .bucket == "cancel")] | length')
  pending=$(jq_int "$checks_json" '[.[] | select(.bucket == "pending")] | length')

  local checks_map
  checks_map=$(echo "$checks_json" | jq '[.[] | {(.name): .state}] | add // {}' 2>/dev/null || echo '{}')

  local cr_state cr_at cr_review_commit cr_is_current
  cr_state=$(jq_str "$cr_review" '.state' 'NONE')
  cr_at=$(jq_str "$cr_review" '.submitted_at' '')
  cr_review_commit=$(jq_str "$cr_review" '.commit_id' '')
  cr_is_current=false
  [ -n "$cr_review_commit" ] && [ "$cr_review_commit" = "$head_sha" ] && cr_is_current=true

  # ── Compute deltas vs previous state ───────────────────────────────────
  local prev_checks prev_cr_state prev_cr_count prev_human prev_human_inline
  prev_checks=$(echo "$prev" | jq '.checks // {}' 2>/dev/null || echo '{}')
  prev_cr_state=$(jq_str "$prev" '.coderabbit_review_state' 'NONE')
  prev_cr_count=$(jq_int "$prev" '.coderabbit_inline_count // 0')
  prev_human=$(echo "$prev" | jq '.human_reviews // {}' 2>/dev/null || echo '{}')
  prev_human_inline=$(jq_int "$prev" '.human_inline_count // 0')
  # On thread-fetch failure, preserve previous counts to avoid false deltas
  if ! $threads_ok; then
    cr_inline_count="$prev_cr_count"
    human_inline_count="$prev_human_inline"
  fi

  local has_changes=false
  local -a delta_lines=()

  # Detect new commit — reset check snapshot to avoid false regressions
  local prev_head_sha
  prev_head_sha=$(jq_str "$prev" '.head_sha' '')
  if [ -n "$head_sha" ] && [ -n "$prev_head_sha" ] && [ "$head_sha" != "$prev_head_sha" ]; then
    has_changes=true
    prev_checks='{}'  # discard stale per-commit check states
    delta_lines+=("  NEW COMMIT: ${prev_head_sha:0:7} -> ${head_sha:0:7} (check history reset)")
  fi

  # CI check state changes
  local check_names_raw
  check_names_raw=$(echo "$checks_map" | jq -r 'keys[]' 2>/dev/null || true)
  if [ -n "$check_names_raw" ]; then
    while IFS= read -r name; do
      [ -z "$name" ] && continue
      local cur_s prev_s
      cur_s=$(echo "$checks_map" | jq -r --arg n "$name" '.[$n] // "UNKNOWN"')
      prev_s=$(echo "$prev_checks" | jq -r --arg n "$name" '.[$n] // "NEW"')
      if [ "$cur_s" != "$prev_s" ]; then
        has_changes=true
        delta_lines+=("  CI: ${name}: ${prev_s} -> ${cur_s}")
      fi
    done <<< "$check_names_raw"
  fi

  # CodeRabbit review state change
  if [ "$cr_state" != "$prev_cr_state" ]; then
    has_changes=true
    delta_lines+=("  CodeRabbit review: ${prev_cr_state} -> ${cr_state}")
  fi

  # CodeRabbit inline comment count change
  local cr_delta=$(( cr_inline_count - prev_cr_count ))
  if [ "$cr_delta" -gt 0 ]; then
    has_changes=true
    delta_lines+=("  CodeRabbit: +${cr_delta} new unresolved thread(s) (total: ${cr_inline_count})")
  elif [ "$cr_delta" -lt 0 ]; then
    has_changes=true
    delta_lines+=("  CodeRabbit: $(( -cr_delta )) thread(s) resolved (total: ${cr_inline_count})")
  fi

  # Human inline comment count change
  local human_inline_delta
  human_inline_delta=$(( human_inline_count - prev_human_inline ))
  if [ "$human_inline_delta" -gt 0 ]; then
    has_changes=true
    delta_lines+=("  Human: +${human_inline_delta} new unresolved thread(s) (total: ${human_inline_count})")
  elif [ "$human_inline_delta" -lt 0 ]; then
    has_changes=true
    delta_lines+=("  Human: $(( -human_inline_delta )) thread(s) resolved (total: ${human_inline_count})")
  fi

  # Human review changes
  local human_names_raw
  human_names_raw=$(echo "$human_reviews_json" | jq -r 'keys[]' 2>/dev/null || true)
  if [ -n "$human_names_raw" ]; then
    while IFS= read -r reviewer; do
      [ -z "$reviewer" ] && continue
      local cur_hr prev_hr
      cur_hr=$(echo "$human_reviews_json" | jq -r --arg r "$reviewer" '.[$r]')
      prev_hr=$(echo "$prev_human" | jq -r --arg r "$reviewer" '.[$r] // "NONE"')
      if [ "$cur_hr" != "$prev_hr" ]; then
        has_changes=true
        delta_lines+=("  Review: ${reviewer}: ${prev_hr} -> ${cur_hr}")
      fi
    done <<< "$human_names_raw"
  fi

  # Human PR comment delta
  local prev_human_comment_count prev_human_comment_last_id
  prev_human_comment_count=$(jq_int "$prev" '.human_comment_count // 0')
  prev_human_comment_last_id=$(jq_int "$prev" '.human_comment_last_id // 0')
  local human_comment_delta=$(( human_comment_count - prev_human_comment_count ))
  if [ "$human_comment_delta" -gt 0 ]; then
    has_changes=true
    # List authors of the new comments
    local new_authors
    new_authors=$(echo "$human_comments_json" | \
      jq -r --argjson last_id "$prev_human_comment_last_id" \
      '[.[] | select(.id > $last_id) | .login] | unique | join(", ")' 2>/dev/null || echo "unknown")
    delta_lines+=("  Comment: +${human_comment_delta} new comment(s) from: ${new_authors}")
  fi

  # Consecutive unchanged poll counter
  local new_unchanged
  if $has_changes || $is_first; then
    new_unchanged=0
  else
    new_unchanged=$(( prev_unchanged + 1 ))
  fi

  # Next adaptive sleep
  local next_sleep
  next_sleep=$(adaptive_sleep "$pending" "$new_unchanged" "$prev_sleep")

  # review_notified_at is set inside the exit-4 branch; default to preserving prev value
  local review_notified_at="${prev_review_notified_at:-}"

  # ── Persist state ───────────────────────────────────────────────────────
  jq -n \
    --argjson pr      "$PR_NUMBER" \
    --arg     first   "$first_polled_at" \
    --arg     last    "$now" \
    --argjson count   "$poll_num" \
    --argjson checks  "$checks_map" \
    --arg     cr_state "$cr_state" \
    --arg     cr_at    "$cr_at" \
    --argjson cr_count "$cr_inline_count" \
    --argjson human          "$human_reviews_json" \
    --argjson human_inline   "$human_inline_count" \
    --argjson human_comment_count  "$human_comment_count" \
    --argjson human_comment_last_id "$human_comment_last_id" \
    --arg     head_sha        "$head_sha" \
    --arg     review_notified "$review_notified_at" \
    --argjson unchanged "$new_unchanged" \
    --argjson sleep     "$next_sleep" \
    '{
      pr_number:                   $pr,
      head_sha:                    $head_sha,
      first_polled_at:             $first,
      last_polled_at:              $last,
      poll_count:                  $count,
      checks:                      $checks,
      coderabbit_review_state:     $cr_state,
      coderabbit_review_at:        $cr_at,
      coderabbit_inline_count:     $cr_count,
      human_reviews:               $human,
      human_inline_count:          $human_inline,
      human_comment_count:         $human_comment_count,
      human_comment_last_id:       $human_comment_last_id,
      consecutive_unchanged_polls: $unchanged,
      next_sleep_seconds:          $sleep,
      review_notified_at:          $review_notified
    }' > "$STATE_FILE"

  # ── Header ──────────────────────────────────────────────────────────────
  echo "============================================================"
  printf "  PR #%s  Poll #%s  (%s)\n" "$PR_NUMBER" "$poll_num" "$now_display"
  if ! $is_first; then
    local last_ts
    last_ts=$(jq_str "$prev" '.last_polled_at' 'unknown')
    printf "  Last polled: %s  |  Unchanged polls: %s\n" "$last_ts" "$new_unchanged"
  fi
  echo "============================================================"
  echo ""

  # ── Report body ─────────────────────────────────────────────────────────
  if $FULL || $is_first; then
    # Full report
    echo "--- PR Details ---"
    echo "$pr_meta" | jq -r 'to_entries[] | "  \(.key): \(.value)"' 2>/dev/null || echo "$pr_meta"
    echo ""

    echo "--- CI Check Runs ---"
    gh pr checks "$PR_NUMBER" --repo "$REPO" 2>/dev/null || echo "  (no checks found)"
    echo ""

    echo "--- CodeRabbit Review ---"
    if [ "$cr_state" != "NONE" ] && [ -n "$cr_state" ]; then
      printf "  State: %s  (at: %s)\n" "$cr_state" "$cr_at"
      if ! $cr_is_current; then
        echo "  NOTE: Review is for an older commit — waiting for CodeRabbit to re-review ${head_sha:0:7}"
      fi
    else
      echo "  (no CodeRabbit review yet)"
    fi
    echo ""

    echo "--- CodeRabbit Unresolved Threads: ${cr_inline_count} ---"
    if [ "$cr_inline_count" -gt 0 ]; then
      local _jq_cr='[.data.repository.pullRequest.reviewThreads.nodes[]? |
          select(.isResolved==false and .isOutdated==false) |
          select(.comments.nodes[0]?.author.__typename=="Bot" and (.comments.nodes[0]?.author.login | startswith("coderabbit")))][-5:] |
        .[] |
        "  \(.comments.nodes[0].path):\(.comments.nodes[0].line // .comments.nodes[0].originalLine // "?")\n  \(.comments.nodes[0].body | split("\n") | .[0:3] | join("\n  "))\n  1. Reply:   gh api repos/\($repo)/pulls/\($pr)/comments/\(.comments.nodes[0].databaseId)/replies -X POST -f body=\"...\"\n  2. Resolve: gh api graphql -f query=\"mutation{resolveReviewThread(input:{threadId:\\\"\(.id)\\\"}){thread{isResolved}}}\"\n"'
      echo "$threads_json" | jq -r --arg repo "$REPO" --arg pr "$PR_NUMBER" "$_jq_cr" \
        2>/dev/null || true
    fi
    echo ""

    echo "--- CodeRabbit Pre-merge Checks ---"
    if [ -n "$walkthrough_body" ] && [ "$walkthrough_body" != "null" ]; then
      echo "$walkthrough_body" | grep -E "(✅|❌|⚠️|pass|fail|warn)" | head -20 || true
    else
      echo "  (no walkthrough yet)"
    fi
    echo ""

    echo "--- Codecov ---"
    if [ -n "$codecov_body" ] && [ "$codecov_body" != "null" ]; then
      echo "$codecov_body" | grep -iE "(Coverage|Diff|patch|project)" | head -10 \
        || echo "  (coverage data present)"
    else
      echo "  (no Codecov report yet)"
    fi
    echo ""

    echo "--- Human Reviews ---"
    local hr_len
    hr_len=$(echo "$human_reviews_json" | jq 'length')
    if [ "$hr_len" -gt 0 ]; then
      echo "$human_reviews_json" | jq -r 'to_entries[] | "  \(.key): \(.value)"'
    else
      echo "  (none yet)"
    fi
    echo ""

    echo "--- Human Unresolved Threads: ${human_inline_count} ---"
    if [ "$human_inline_count" -gt 0 ]; then
      local _jq_human='[.data.repository.pullRequest.reviewThreads.nodes[]? |
          select(.isResolved==false and .isOutdated==false) |
          select(.comments.nodes[0]?.author.__typename=="User")][-5:] |
        .[] |
        "  \(.comments.nodes[0].author.login) on \(.comments.nodes[0].path):\(.comments.nodes[0].line // .comments.nodes[0].originalLine // "?")\n  \(.comments.nodes[0].body | split("\n") | .[0:3] | join("\n  "))\n  1. Reply:   gh api repos/\($repo)/pulls/\($pr)/comments/\(.comments.nodes[0].databaseId)/replies -X POST -f body=\"...\"\n  2. Resolve: gh api graphql -f query=\"mutation{resolveReviewThread(input:{threadId:\\\"\(.id)\\\"}){thread{isResolved}}}\"\n"'
      echo "$threads_json" | jq -r --arg repo "$REPO" --arg pr "$PR_NUMBER" "$_jq_human" \
        2>/dev/null || true
    fi
    echo ""

    echo "--- Human Comments: ${human_comment_count} ---"
    if [ "$human_comment_count" -gt 0 ]; then
      echo "$human_comments_json" | jq -r '
        .[-3:] | .[] |
        "  \(.login) (\(.created_at | split("T")[0])): \(.body | split("\n") | .[0:2] | join(" "))"' \
        2>/dev/null || true
    else
      echo "  (none)"
    fi
    echo ""

    echo "--- JIRA Bot ---"
    if [ -n "$jira_body" ] && [ "$jira_body" != "null" ]; then
      echo "$jira_body" | head -10
    else
      echo "  (no JIRA bot comment)"
    fi
    echo ""

  else
    # Delta-only report
    echo "--- Changes Since Last Poll ---"
    if [ "${#delta_lines[@]}" -eq 0 ]; then
      echo "  (no changes detected)"
    else
      for line in "${delta_lines[@]}"; do
        echo "$line"
      done
    fi
    echo ""
    echo "  Tip: run with --full for complete report, or check ${STATE_FILE}"
    echo ""
  fi

  # ── Summary (always shown) ───────────────────────────────────────────────
  echo "============================================================"
  echo "  SUMMARY"
  echo "============================================================"

  local hr_count hr_approved review_decision
  hr_count=$(echo "$human_reviews_json" | jq 'length')
  hr_approved=$(echo "$human_reviews_json" | \
    jq '[to_entries[] | select(.value == "APPROVED")] | length')
  review_decision=$(jq_str "$pr_meta" '.review_decision' '')

  printf "  CI:         %s/%s passed, %s failed, %s pending\n" \
    "$pass" "$total" "$fail" "$pending"
  local _cr_label="$cr_state"
  ! $cr_is_current && [ "$cr_state" != "NONE" ] && _cr_label="${cr_state} (pending re-review)"
  printf "  CodeRabbit: %-36s inline: %s\n" "$_cr_label" "$cr_inline_count"
  printf "  Human:      %s/%s approved  |  unresolved threads: %s\n" "$hr_approved" "$hr_count" "$human_inline_count"
  echo ""

  # Determine exit code and action message
  local exit_code=0

  if [ "$fail" -gt 0 ]; then
    echo "  ACTION REQUIRED: Fix CI failures:"
    echo "$checks_json" | \
      jq -r '.[] | select(.bucket == "fail" or .bucket == "cancel") | "    - \(.name)"' \
      2>/dev/null || true
    exit_code=1

  elif [ "$human_inline_count" -gt 0 ] || [ "$cr_inline_count" -gt 0 ]; then
    local _msg=""
    [ "$human_inline_count" -gt 0 ] && _msg="${human_inline_count} human thread(s)"
    [ "$cr_inline_count" -gt 0 ] && _msg="${_msg:+$_msg, }${cr_inline_count} CodeRabbit thread(s)"
    printf "  ACTION REQUIRED: Address inline review comments: %s\n" "$_msg"
    exit_code=3

  elif ! $is_first && [ "$human_comment_delta" -gt 0 ]; then
    printf "  ACTION REQUIRED: %s new comment(s) — read and respond before continuing\n" "$human_comment_delta"
    echo "$human_comments_json" | jq -r --argjson last_id "$prev_human_comment_last_id" \
      '[.[] | select(.id > $last_id)] | .[] |
       "  \(.login): \(.body | split("\n") | .[0:2] | join(" "))"' 2>/dev/null || true
    exit_code=3

  elif [ "$review_decision" = "REVIEW_CHANGES_REQUESTED" ] || \
       { [ "$hr_count" -gt 0 ] && [ "$(echo "$human_reviews_json" | jq '[to_entries[] | select(.value == "CHANGES_REQUESTED")] | length')" -gt 0 ]; }; then
    echo "  ACTION REQUIRED: Reviewer(s) requested changes"
    echo "$human_reviews_json" | jq -r 'to_entries[] | select(.value == "CHANGES_REQUESTED") | "    - \(.key)"' 2>/dev/null || true
    exit_code=3

  elif ! $cr_is_current && [ "$cr_state" != "NONE" ] && [ "$pending" -eq 0 ]; then
    echo "  WAITING: CodeRabbit re-review pending for ${head_sha:0:7}"
    exit_code=2

  elif [ "$pending" -gt 0 ]; then
    printf "  WAITING: %s check(s) still running" "$pending"
    if ! $ONCE && [ "$next_sleep" -gt 0 ]; then
      printf " — next poll in %ss (adaptive)\n" "$next_sleep"
    else
      echo ""
    fi
    exit_code=2

  elif ! $threads_ok; then
    echo "  WAITING: review-thread fetch failed — will retry next poll"
    exit_code=2

  elif [ "$review_decision" != "REVIEW_APPROVED" ] && { [ "$hr_count" -eq 0 ] || [ "$hr_approved" -eq 0 ]; }; then
    echo "  WAITING: Awaiting human review approval"
    if [ -z "$prev_review_notified_at" ]; then
      local ci_summary
      ci_summary=$(printf "CI: %s/%s passed | CodeRabbit: %s | Unresolved threads: CR=%s Human=%s" \
        "$pass" "$total" "$cr_state" "$cr_inline_count" "$human_inline_count")
      if notify_for_review "$ci_summary"; then
        review_notified_at="$now"
        # Persist immediately so subsequent polls skip the notify guard
        local _tmp
        _tmp=$(mktemp) && jq --arg v "$review_notified_at" '.review_notified_at = $v' \
          "$STATE_FILE" > "$_tmp" && mv "$_tmp" "$STATE_FILE"
      else
        echo "  WARN: reviewer notification incomplete — will retry on next poll."
      fi
    else
      review_notified_at="${prev_review_notified_at:-}"
    fi
    exit_code=4

  else
    echo "  ALL CHECKS PASSING — ready to merge"
    exit_code=0
  fi

  echo ""
  echo "  State: ${STATE_FILE}  (poll #${poll_num}, first: ${first_polled_at})"
  echo "============================================================"

  return "$exit_code"
}

# ── Main loop ─────────────────────────────────────────────────────────────────
iter=0
while true; do
  iter=$(( iter + 1 ))

  if [ "$MAX_POLLS" -gt 0 ] && [ "$iter" -gt "$MAX_POLLS" ]; then
    echo "Max polls (${MAX_POLLS}) reached. Stopping." >&2
    exit 2
  fi

  set +e
  do_poll
  RC=$?
  set -e

  if $ONCE; then
    exit "$RC"
  fi

  if [ "$MAX_POLLS" -gt 0 ] && [ "$iter" -ge "$MAX_POLLS" ]; then
    echo "Max polls (${MAX_POLLS}) reached. Stopping." >&2
    exit "$RC"
  fi

  case "$RC" in
    0)
      echo "All checks passing. Polling complete."
      exit 0
      ;;
    1)
      echo "CI failures detected — fix and re-run: bash .claude/scripts/poll-pr.sh ${PR_NUMBER}"
      exit 1
      ;;
    3)
      echo "Review feedback requires attention — address and re-run: bash .claude/scripts/poll-pr.sh ${PR_NUMBER}"
      exit 3
      ;;
    2)
      # CI/checks still pending — keep polling
      SLEEP_SECS=$(jq -r '.next_sleep_seconds // 120' "$STATE_FILE" 2>/dev/null || echo 120)
      [ "$SLEEP_SECS" -le 0 ] && SLEEP_SECS=120
      printf "\nSleeping %ss (adaptive backoff)... Ctrl+C to stop.\n\n" "$SLEEP_SECS"
      sleep "$SLEEP_SECS"
      ;;
    4)
      # Awaiting human review — keep polling at a slower cadence (5 min min)
      SLEEP_SECS=300
      printf "
Awaiting human review — next check in %ss...

" "$SLEEP_SECS"
      sleep "$SLEEP_SECS"
      ;;
    *)
      echo "Unexpected exit code ${RC}. Stopping." >&2
      exit "$RC"
      ;;
  esac
done
