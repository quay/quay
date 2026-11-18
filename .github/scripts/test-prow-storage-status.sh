#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
script="$script_dir/prow-storage-status.sh"

work="$(mktemp -d)"
trap 'rm -r -- "$work"' EXIT

# Stub gh: serves fixtures from $STUB and logs status posts to $STUB/posts.
mkdir "$work/bin"
cat >"$work/bin/gh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
shift # api
method=GET path= filter= fields=()
while [ $# -gt 0 ]; do
  case $1 in
  -X) method=$2; shift 2 ;;
  -f) fields+=("${2#*=}"); shift 2 ;;
  --jq) filter=$2; shift 2 ;;
  --paginate) shift ;;
  *) path=$1; shift ;;
  esac
done
if [ "$method" = POST ]; then
  (IFS='|'; echo "${fields[*]}") >>"$STUB/posts"
  exit 0
fi
case $path in
*/files) body=$(cat "$STUB/files.json") ;;
*/status*)
  n=$(($(cat "$STUB/status-calls" 2>/dev/null || echo 0) + 1))
  echo "$n" >"$STUB/status-calls"
  if [ -f "$STUB/status.$n.json" ]; then body=$(cat "$STUB/status.$n.json"); else body=$(cat "$STUB/status.json"); fi
  ;;
*/pulls/*)
  n=$(($(cat "$STUB/pr-calls" 2>/dev/null || echo 0) + 1))
  echo "$n" >"$STUB/pr-calls"
  if [ -f "$STUB/pr.$n.json" ]; then body=$(cat "$STUB/pr.$n.json"); else body=$(cat "$STUB/pr.json"); fi
  ;;
*) echo "unexpected gh api $path" >&2; exit 1 ;;
esac
if [ -n "$filter" ]; then jq -r "$filter" <<<"$body"; else echo "$body"; fi
EOF
chmod +x "$work/bin/gh"

export PATH="$work/bin:$PATH"
export GITHUB_REPOSITORY=quay/quay GITHUB_SERVER_URL=https://github.com GITHUB_RUN_ID=1
export PROW_STATUS_POLL_SECONDS=0
sha=abc123
url=https://github.com/quay/quay/actions/runs/1
failures=0

statuses() { # context=state ...
  local args=() kv
  for kv in "$@"; do args+=("{\"context\":\"${kv%=*}\",\"state\":\"${kv#*=}\"}"); done
  (IFS=,; echo "{\"statuses\":[${args[*]}]}")
}

# setup <file> <head-sha>
setup() {
  export STUB="$work/case"
  rm -rf -- "$STUB"
  mkdir "$STUB"
  echo "[{\"filename\":\"$1\"},{\"filename\":\"web/package.json\"}]" >"$STUB/files.json"
  echo "{\"state\":\"open\",\"base\":{\"ref\":\"master\"},\"head\":{\"sha\":\"$2\"}}" >"$STUB/pr.json"
  statuses >"$STUB/status.json"
}

# check <name> <expected posts, newline separated> <script args...>
check() {
  local name=$1 want=$2 got
  shift 2
  if ! "$script" 7 "$@" >"$STUB/out" 2>&1; then
    echo "FAIL ($name): script exited non-zero"
    cat "$STUB/out"
    failures=$((failures + 1))
    return
  fi
  got=$(cat "$STUB/posts" 2>/dev/null || true)
  if [ "$got" != "$want" ]; then
    echo "FAIL ($name): posted"
    echo "$got"
    echo "want"
    echo "$want"
    failures=$((failures + 1))
    return
  fi
  echo "PASS: $name"
}

all_success=(ci/prow/aws-s3=success ci/prow/gcp-gcs=success ci/prow/azure-blob=success)

setup README.md "$sha"
check "no manifest touched" "success|CI / Prow / E2E|no storage jobs selected|$url" "$sha"

setup requirements.txt "$sha"
statuses "${all_success[@]}" ci/prow/other=failure >"$STUB/status.json"
check "all storage jobs passed" "success|CI / Prow / E2E|storage jobs passed|$url" "$sha"

setup pyproject.toml "$sha"
statuses ci/prow/aws-s3=success ci/prow/gcp-gcs=failure ci/prow/azure-blob=pending >"$STUB/status.json"
check "one storage job failed" "failure|CI / Prow / E2E|ci/prow/gcp-gcs failed|$url" "$sha"

setup pyproject.toml "$sha"
statuses ci/prow/aws-s3=success ci/prow/gcp-gcs=error ci/prow/azure-blob=pending >"$STUB/status.json"
check "one storage job errored" "failure|CI / Prow / E2E|ci/prow/gcp-gcs failed|$url" "$sha"

setup constraints.txt "$sha"
statuses ci/prow/aws-s3=success ci/prow/gcp-gcs=success >"$STUB/status.json"
check "one storage job missing" "pending|CI / Prow / E2E|waiting for ci/prow/azure-blob|$url" "$sha"

setup requirements.txt other
statuses "${all_success[@]}" >"$STUB/status.json"
check "stale head posts nothing" "" "$sha"

setup requirements-build.txt "$sha"
statuses ci/prow/aws-s3=pending >"$STUB/status.1.json"
statuses "${all_success[@]}" >"$STUB/status.2.json"
check "wait: pending then success" "pending|CI / Prow / E2E|waiting for storage jobs|$url
success|CI / Prow / E2E|storage jobs passed|$url" "$sha" --wait

# The head goes stale after the pending post: the loop stops before polling statuses.
setup requirements.txt "$sha"
sed "s/$sha/other/" "$STUB/pr.json" >"$STUB/pr.2.json"
statuses "${all_success[@]}" >"$STUB/status.json"
check "wait: stale head stops polling" "pending|CI / Prow / E2E|waiting for storage jobs|$url" "$sha" --wait
if [ -f "$STUB/status-calls" ]; then
  echo "FAIL (wait: stale head stops polling): polled statuses"
  failures=$((failures + 1))
fi

setup requirements.txt "$sha"
rm -- "$STUB/pr.json"
if "$script" 7 "$sha" >"$STUB/out" 2>&1; then
  echo "FAIL (pull API error): script exited zero"
  failures=$((failures + 1))
else
  echo "PASS: pull API error"
fi

setup requirements.txt "$sha"
statuses ci/prow/aws-s3=success >"$STUB/status.json"
PROW_STATUS_DEADLINE_SECONDS=0 check "wait: deadline fails" "pending|CI / Prow / E2E|waiting for storage jobs|$url
failure|CI / Prow / E2E|timed out waiting for ci/prow/gcp-gcs ci/prow/azure-blob|$url" "$sha" --wait

if [ "$failures" -ne 0 ]; then
  echo "$failures case(s) failed"
  exit 1
fi

echo "all cases passed"
