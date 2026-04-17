#!/bin/bash
# poll-pr.sh -- Stateful PR poller: GitHub Actions CI, CodeRabbit, Codecov, human reviews.
#
# Usage: bash .claude/scripts/poll-pr.sh <PR_NUMBER> [OPTIONS]
#
# Options:
#   --repo OWNER/REPO   Repository (default: quay/quay)
#   --once              Single poll; exit immediately (default: loop until done)
#   --full              Always print full report (default: delta-only on re-polls)
#   --max-polls N       Stop after N total polls (default: unlimited)
#
# Exit codes:
#   0  All checks pass — ready to merge
#   1  CI failures — fix required
#   2  Checks still pending — re-poll later
#   3  CodeRabbit inline comments — address required
#   4  Awaiting human review — nothing actionable yet
#
# State file: .claude/poll-state/pr-<NUMBER>.json
#   Tracks check states, review states, comment counts, adaptive sleep, and poll history.
#   Added to .gitignore automatically on first run.

set -euo pipefail

PR_NUMBER="${1:?Usage: poll-pr.sh <PR_NUMBER> [--repo OWNER/REPO] [--once] [--full] [--max-polls N]}"
shift

REPO="quay/quay"
ONCE=false
FULL=false
MAX_POLLS=0  # 0 = unlimited

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)       REPO="$2"; shift 2 ;;
    --once)       ONCE=true; shift ;;
    --full)       FULL=true; shift ;;
    --max-polls)  MAX_POLLS="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

# ── State file setup ─────────────────────────────────────────────────────────
STATE_DIR=".claude/poll-state"
STATE_FILE="${STATE_DIR}/pr-${PR_NUMBER}.json"
mkdir -p "$STATE_DIR"

# Ensure state dir is gitignored (idempotent)
GITIGNORE=".gitignore"
if [ -f "$GITIGNORE" ] && ! grep -qF ".claude/poll-state" "$GITIGNORE" 2>/dev/null; then
  printf '\n# poll-pr state (auto-generated, do not commit)\n.claude/poll-state/\n' >> "$GITIGNORE"
fi

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

  checks_json=$(gh pr checks "$PR_NUMBER" --repo "$REPO" --json name,state \
    2>/dev/null || echo '[]')

  cr_review=$(gh api --paginate "repos/${REPO}/pulls/${PR_NUMBER}/reviews" \
    --jq '[.[] | select(.user.login == "coderabbitai[bot]")]' \
    2>/dev/null | jq -s 'flatten | last // {}' || echo '{}')

  cr_inline_count=$(gh api --paginate "repos/${REPO}/pulls/${PR_NUMBER}/comments" \
    --jq '[.[] | select(.user.login == "coderabbitai[bot]")] | length' \
    2>/dev/null | jq -s 'add // 0' || echo '0')

  human_inline_count=$(gh api --paginate "repos/${REPO}/pulls/${PR_NUMBER}/comments" \
    --jq '[.[] | select(
            .user.login != "coderabbitai[bot]" and
            (.user.login | endswith("[bot]") | not) and
            .user.login != "openshift-ci-robot"
          )] | length' \
    2>/dev/null | jq -s 'add // 0' || echo '0')

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

  # ── Compute check summary ───────────────────────────────────────────────
  local total pass fail pending
  total=$(jq_int "$checks_json" 'length')
  pass=$(jq_int "$checks_json" '[.[] | select(.state == "SUCCESS")] | length')
  fail=$(jq_int "$checks_json" '[.[] | select(.state == "FAILURE" or .state == "ERROR")] | length')
  pending=$(jq_int "$checks_json" \
    '[.[] | select(.state == "PENDING" or .state == "QUEUED" or .state == "IN_PROGRESS" or .state == "WAITING")] | length')

  local checks_map
  checks_map=$(echo "$checks_json" | jq '[.[] | {(.name): .state}] | add // {}' 2>/dev/null || echo '{}')

  local cr_state cr_at cr_review_commit cr_is_current
  cr_state=$(jq_str "$cr_review" '.state' 'NONE')
  cr_at=$(jq_str "$cr_review" '.submitted_at' '')
  cr_review_commit=$(jq_str "$cr_review" '.commit_id' '')
  cr_is_current=false
  [ -n "$cr_review_commit" ] && [ "$cr_review_commit" = "$head_sha" ] && cr_is_current=true

  # ── Compute deltas vs previous state ───────────────────────────────────
  local prev_checks prev_cr_state prev_cr_count prev_human
  prev_checks=$(echo "$prev" | jq '.checks // {}' 2>/dev/null || echo '{}')
  prev_cr_state=$(jq_str "$prev" '.coderabbit_review_state' 'NONE')
  prev_cr_count=$(jq_int "$prev" '.coderabbit_inline_count // 0')
  prev_human=$(echo "$prev" | jq '.human_reviews // {}' 2>/dev/null || echo '{}')

  local has_changes=false
  local -a delta_lines=()

  # Detect new commit — reset check snapshot to avoid false regressions
  local prev_head_sha sha_changed=false
  prev_head_sha=$(jq_str "$prev" '.head_sha' '')
  if [ -n "$head_sha" ] && [ -n "$prev_head_sha" ] && [ "$head_sha" != "$prev_head_sha" ]; then
    sha_changed=true
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
    delta_lines+=("  CodeRabbit: +${cr_delta} new inline comment(s) (total: ${cr_inline_count})")
  elif [ "$cr_delta" -lt 0 ]; then
    has_changes=true
    delta_lines+=("  CodeRabbit: ${cr_delta} comment(s) resolved (total: ${cr_inline_count})")
  fi

  # Human inline comment count change
  local prev_human_inline human_inline_delta
  prev_human_inline=$(jq_int "$prev" '.human_inline_count // 0')
  human_inline_delta=$(( human_inline_count - prev_human_inline ))
  if [ "$human_inline_delta" -gt 0 ]; then
    has_changes=true
    delta_lines+=("  Human: +${human_inline_delta} new inline comment(s) (total: ${human_inline_count})")
  elif [ "$human_inline_delta" -lt 0 ]; then
    has_changes=true
    delta_lines+=("  Human: ${human_inline_delta} inline comment(s) resolved (total: ${human_inline_count})")
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
    --arg     head_sha        "$head_sha" \
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
      consecutive_unchanged_polls: $unchanged,
      next_sleep_seconds:          $sleep
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

    echo "--- CodeRabbit Inline Comments on current commit: ${cr_inline_count} ---"
    if [ "$cr_inline_count" -gt 0 ]; then
      gh api --paginate "repos/${REPO}/pulls/${PR_NUMBER}/comments" \
        --jq --arg sha "$head_sha" \
        '[.[] | select(.user.login == "coderabbitai[bot]" and .commit_id == $sha)] | .[-3:] | .[] |
              "  \(.path):\(.line // .original_line // \"?\")\n  \(.body | split(\"\n\") | .[0:3] | join(\"\n  \"))\n"' \
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

    echo "--- Human Inline Comments: ${human_inline_count} ---"
    if [ "$human_inline_count" -gt 0 ]; then
      gh api "repos/${REPO}/pulls/${PR_NUMBER}/comments" \
        --jq '[.[] | select(
                .user.login != "coderabbitai[bot]" and
                (.user.login | endswith("[bot]") | not) and
                .user.login != "openshift-ci-robot"
              )] | .[-5:] | .[] |
              "  \(.user.login) on \(.path):\(.line // .original_line // "?")\n  \(.body | split("\n") | .[0:3] | join("\n  "))\n"' \
        2>/dev/null || true
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

  local hr_count hr_approved
  hr_count=$(echo "$human_reviews_json" | jq 'length')
  hr_approved=$(echo "$human_reviews_json" | \
    jq '[to_entries[] | select(.value == "APPROVED")] | length')

  printf "  CI:         %s/%s passed, %s failed, %s pending\n" \
    "$pass" "$total" "$fail" "$pending"
  local _cr_label="$cr_state"
  ! $cr_is_current && [ "$cr_state" != "NONE" ] && _cr_label="${cr_state} (pending re-review)"
  printf "  CodeRabbit: %-36s inline: %s\n" "$_cr_label" "$cr_inline_count"
  printf "  Human:      %s/%s approved  |  inline comments: %s\n" "$hr_approved" "$hr_count" "$human_inline_count"
  echo ""

  # Determine exit code and action message
  local exit_code=0

  if [ "$fail" -gt 0 ]; then
    echo "  ACTION REQUIRED: Fix CI failures:"
    echo "$checks_json" | \
      jq -r '.[] | select(.state == "FAILURE" or .state == "ERROR") | "    - \(.name)"' \
      2>/dev/null || true
    exit_code=1

  elif [ "$human_inline_count" -gt 0 ] || ( [ "$cr_inline_count" -gt 0 ] && $cr_is_current ); then
    local _msg=""
    [ "$human_inline_count" -gt 0 ] && _msg="${human_inline_count} human comment(s)"
    ( [ "$cr_inline_count" -gt 0 ] && $cr_is_current ) && _msg="${_msg:+$_msg, }${cr_inline_count} CodeRabbit comment(s)"
    printf "  ACTION REQUIRED: Address inline review comments: %s\n" "$_msg"
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

  elif [ "$hr_count" -gt 0 ] &&        [ "$(echo "$human_reviews_json" | jq '[to_entries[] | select(.value == "CHANGES_REQUESTED")] | length')" -gt 0 ]; then
    echo "  ACTION REQUIRED: Reviewer(s) requested changes"
    echo "$human_reviews_json" | jq -r 'to_entries[] | select(.value == "CHANGES_REQUESTED") | "    - \(.key)"' 2>/dev/null || true
    exit_code=3

  elif [ "$hr_count" -eq 0 ] || [ "$hr_approved" -eq 0 ]; then
    echo "  WAITING: Awaiting human review approval"
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
      echo "CodeRabbit comments require attention — address and re-run: bash .claude/scripts/poll-pr.sh ${PR_NUMBER}"
      exit 3
      ;;
    2|4)
      # Still pending (2) or awaiting human review (4) — keep polling
      SLEEP_SECS=$(jq -r '.next_sleep_seconds // 120' "$STATE_FILE" 2>/dev/null || echo 120)
      # Floor: exit 4 (no pending checks, just waiting on humans) must not spin at 0s
      [ "$SLEEP_SECS" -le 0 ] && SLEEP_SECS=300
      printf "\nSleeping %ss (adaptive backoff)... Ctrl+C to stop.\n\n" "$SLEEP_SECS"
      sleep "$SLEEP_SECS"
      ;;
    *)
      echo "Unexpected exit code ${RC}. Stopping." >&2
      exit "$RC"
      ;;
  esac
done
