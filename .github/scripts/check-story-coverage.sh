#!/usr/bin/env bash
set -euo pipefail

# Fails the build if NEW components under web/src/components/ lack a .stories.tsx file.
# Only enforces on added files (git diff --diff-filter=A), not modified ones.

base_ref="${GITHUB_BASE_REF:-master}"
missing=()

while IFS= read -r file; do
  [[ -z "$file" ]] && continue

  # Skip test files, index files, CSS/SCSS, stories themselves
  case "$file" in
    *.test.tsx|*.test.ts|*.spec.tsx|*.spec.ts) continue ;;
    */index.tsx|*/index.ts) continue ;;
    *.css|*.scss|*.sass) continue ;;
    *.stories.tsx|*.stories.ts) continue ;;
  esac

  # Only check .tsx component files
  [[ "$file" != *.tsx ]] && continue

  # Derive expected story path
  story_file="${file%.tsx}.stories.tsx"
  if [[ ! -f "$story_file" ]]; then
    missing+=("$file")
  fi
done < <(git diff --diff-filter=A --name-only "origin/${base_ref}...HEAD" -- src/components/)

if [[ ${#missing[@]} -gt 0 ]]; then
  echo "::error::New components missing stories:"
  for f in "${missing[@]}"; do
    echo "  - $f"
  done
  echo ""
  echo "Add a .stories.tsx file next to each new component."
  exit 1
fi

echo "All new components have stories."
