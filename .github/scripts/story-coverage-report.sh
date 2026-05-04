#!/usr/bin/env bash
set -euo pipefail

# Scans all components under web/src/components/, counts stories, and appends
# a coverage table to $GITHUB_STEP_SUMMARY.

total=0
covered=0
uncovered=()

while IFS= read -r file; do
  # Skip non-component files
  case "$file" in
    *.test.tsx|*.test.ts|*.spec.tsx|*.spec.ts) continue ;;
    */index.tsx|*/index.ts) continue ;;
    *.css|*.scss|*.sass) continue ;;
    *.stories.tsx|*.stories.ts) continue ;;
    *.d.ts) continue ;;
  esac

  [[ "$file" != *.tsx ]] && continue

  total=$((total + 1))
  story_file="${file%.tsx}.stories.tsx"
  if [[ -f "$story_file" ]]; then
    covered=$((covered + 1))
  else
    uncovered+=("$file")
  fi
done < <(find src/components/ -type f -name '*.tsx' | sort)

if [[ $total -eq 0 ]]; then
  echo "No components found."
  exit 0
fi

pct=$((covered * 100 / total))

# Write to GITHUB_STEP_SUMMARY if available, otherwise stdout
output="${GITHUB_STEP_SUMMARY:-/dev/stdout}"

{
  echo "## Storybook Coverage"
  echo ""
  echo "| Metric | Value |"
  echo "|--------|-------|"
  echo "| Components | $total |"
  echo "| With stories | $covered |"
  echo "| Coverage | ${pct}% |"
  echo ""

  if [[ ${#uncovered[@]} -gt 0 ]]; then
    echo "<details>"
    echo "<summary>Components missing stories (${#uncovered[@]})</summary>"
    echo ""
    for f in "${uncovered[@]}"; do
      echo "- \`$f\`"
    done
    echo ""
    echo "</details>"
  fi
} >> "$output"

echo "Story coverage: ${covered}/${total} (${pct}%)"
