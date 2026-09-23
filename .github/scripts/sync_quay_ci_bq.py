#!/usr/bin/env python3
"""
Fetch Quay CI workflow runs and Playwright test results from GitHub Actions,
then insert them into Google BigQuery for analytics and trend tracking.

Environment variables:
    GITHUB_TOKEN   - GitHub PAT with actions:read scope (required)
    PROJECT_ID     - GCP project ID (default: quay-devel)
    DATASET_ID     - BigQuery dataset (default: quay_ci)
    DAYS_BACK      - Number of days to look back (default: 7)
    GOOGLE_APPLICATION_CREDENTIALS - set automatically by google-github-actions/auth
"""

import hashlib
import io
import json
import os
import re
import time
import zipfile
from datetime import datetime, timedelta, timezone

import requests
from google.cloud import bigquery

# =========================================================
# 1. Configuration
# =========================================================
PROJECT_ID = os.environ.get("PROJECT_ID", "quay-devel")
DATASET_ID = os.environ.get("DATASET_ID", "quay_ci")
JOBS_TABLE = "quay_ci_jobs"
TESTS_TABLE = "quay_ci_test_cases"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO = "quay/quay"
DAYS_BACK = int(os.environ.get("DAYS_BACK", "7"))

if not PROJECT_ID or not GITHUB_TOKEN:
    raise ValueError("Missing PROJECT_ID or GITHUB_TOKEN environment variables.")

HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "Authorization": f"Bearer {GITHUB_TOKEN}",
}


# =========================================================
# 2. BigQuery Schema Setup
# =========================================================
def setup_bigquery_tables(client: bigquery.Client):
    """Creates the dataset and both tables if they do not exist."""
    dataset_ref = bigquery.Dataset(f"{PROJECT_ID}.{DATASET_ID}")
    dataset_ref.location = "US"
    client.create_dataset(dataset_ref, exists_ok=True)

    # --- Jobs Table ---
    jobs_schema = [
        bigquery.SchemaField("job_id", "INTEGER"),
        bigquery.SchemaField("run_id", "INTEGER"),
        bigquery.SchemaField("run_attempt", "INTEGER"),
        bigquery.SchemaField("workflow_name", "STRING"),
        bigquery.SchemaField("job_name", "STRING"),
        bigquery.SchemaField("head_sha", "STRING"),
        bigquery.SchemaField("branch_name", "STRING"),
        bigquery.SchemaField("pr_number", "INTEGER"),
        bigquery.SchemaField("conclusion", "STRING"),
        bigquery.SchemaField("started_at", "TIMESTAMP"),
        bigquery.SchemaField("completed_at", "TIMESTAMP"),
        bigquery.SchemaField("runner_group", "STRING"),
    ]
    jobs_table = bigquery.Table(f"{PROJECT_ID}.{DATASET_ID}.{JOBS_TABLE}", schema=jobs_schema)
    jobs_table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY, field="started_at"
    )
    client.create_table(jobs_table, exists_ok=True)

    # --- Test Cases Table ---
    tests_schema = [
        bigquery.SchemaField("run_id", "INTEGER"),
        bigquery.SchemaField("head_sha", "STRING"),
        bigquery.SchemaField("branch_name", "STRING"),
        bigquery.SchemaField("pr_number", "INTEGER"),
        bigquery.SchemaField("test_suite", "STRING"),
        bigquery.SchemaField("test_name", "STRING"),
        bigquery.SchemaField("status", "STRING"),
        bigquery.SchemaField("duration_seconds", "FLOAT64"),
        bigquery.SchemaField("execution_date", "TIMESTAMP"),
    ]
    tests_table = bigquery.Table(f"{PROJECT_ID}.{DATASET_ID}.{TESTS_TABLE}", schema=tests_schema)
    tests_table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY, field="execution_date"
    )
    client.create_table(tests_table, exists_ok=True)

    print("Verified BigQuery schemas for Jobs and Test Cases.")


# =========================================================
# 3. Helper Functions
# =========================================================
def handle_rate_limit(response):
    """Pauses execution if GitHub rate limits are hit."""
    if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
        reset_timestamp = int(response.headers.get("X-RateLimit-Reset", 0))
        sleep_seconds = max(reset_timestamp - time.time(), 0) + 5
        print(f"\n[RATE LIMIT] Sleeping for {sleep_seconds / 60:.1f} minutes...")
        time.sleep(sleep_seconds)
        return True
    return False


def extract_pr_number(run: dict) -> int | None:
    """Extracts PR number from pull_requests array, with fallback to branch name or title."""
    prs = run.get("pull_requests", [])
    if prs and len(prs) > 0:
        return prs[0].get("number")

    head_branch = run.get("head_branch", "")
    match = re.search(r"(?:pull|pr)[/-](\d+)", head_branch, re.IGNORECASE)
    if match:
        return int(match.group(1))

    display_title = run.get("display_title", "")
    match_title = re.search(r"#(\d+)", display_title)
    if match_title:
        return int(match_title.group(1))

    return None


def get_existing_run_ids(bq_client: bigquery.Client) -> set:
    """Fetches already ingested run_ids to prevent re-fetching/re-inserting.

    Raises on query failure to avoid duplicating all data when BQ is unreachable.
    """
    query = f"SELECT DISTINCT run_id FROM `{PROJECT_ID}.{DATASET_ID}.{JOBS_TABLE}`"
    query_job = bq_client.query(query)
    existing_ids = {row["run_id"] for row in query_job.result()}
    print(f"Found {len(existing_ids)} existing run_ids in BigQuery. Will skip these.")
    return existing_ids


# =========================================================
# 4. Artifact & Test Case Extractor (Playwright JSON)
# =========================================================
def fetch_and_insert_test_artifacts(
    bq_client, run_id, head_sha, branch_name, pr_number, execution_date
):
    """Downloads ZIP artifacts, parses Playwright JSON, and streams into BQ using MD5 row_ids."""
    artifacts_url = f"https://api.github.com/repos/{REPO}/actions/runs/{run_id}/artifacts"
    while True:
        resp = requests.get(artifacts_url, headers=HEADERS, timeout=(10, 60))
        if not handle_rate_limit(resp):
            break
    if resp.status_code != 200:
        print(f"    -> Failed to fetch artifacts for run {run_id}: HTTP {resp.status_code}")
        return

    artifacts = resp.json().get("artifacts", [])
    test_cases_to_insert = []
    row_ids = []

    def process_suite(suite, parent_title=""):
        parts = [parent_title, suite.get("title", "")]
        suite_title = " > ".join(p for p in parts if p)
        if not suite_title:
            suite_title = suite.get("file", "Unknown Suite")

        for spec in suite.get("specs", []):
            test_name = spec.get("title", "Unknown Test")

            for test_idx, test in enumerate(spec.get("tests", [])):
                for result_idx, result in enumerate(test.get("results", [])):
                    raw_status = result.get("status", "unknown")
                    duration_sec = result.get("duration", 0) / 1000.0

                    bq_status = raw_status
                    if raw_status in ["timedOut", "unexpected"]:
                        bq_status = "failed"
                    elif raw_status in ["interrupted", "flaky"]:
                        bq_status = "skipped"

                    clean_suite = suite_title[:250]
                    clean_name = test_name[:250]

                    test_cases_to_insert.append(
                        {
                            "run_id": run_id,
                            "head_sha": head_sha,
                            "branch_name": branch_name,
                            "pr_number": pr_number,
                            "test_suite": clean_suite,
                            "test_name": clean_name,
                            "status": bq_status,
                            "duration_seconds": duration_sec,
                            "execution_date": execution_date,
                        }
                    )

                    raw_id_str = f"{run_id}_{clean_suite}_{clean_name}_{test_idx}_{result_idx}"
                    deterministic_id = hashlib.md5(
                        raw_id_str.encode("utf-8"), usedforsecurity=False
                    ).hexdigest()
                    row_ids.append(deterministic_id)

        for nested_suite in suite.get("suites", []):
            process_suite(nested_suite, suite_title)

    for artifact in artifacts:
        if "test" in artifact["name"].lower() or "playwright" in artifact["name"].lower():
            zip_url = artifact["archive_download_url"]
            zip_resp = requests.get(zip_url, headers=HEADERS, timeout=(10, 120))
            if zip_resp.status_code != 200:
                continue

            try:
                with zipfile.ZipFile(io.BytesIO(zip_resp.content)) as z:
                    for filename in z.namelist():
                        if filename.endswith(".json") and "results" in filename:
                            print(f"    -> Found Playwright JSON in run {run_id}: {filename}")
                            json_content = z.read(filename).decode("utf-8")
                            playwright_data = json.loads(json_content)

                            for suite in playwright_data.get("suites", []):
                                process_suite(suite)

            except Exception as e:
                print(f"    -> Error parsing JSON artifact for run {run_id}: {e}")

    if test_cases_to_insert:
        table_id = f"{PROJECT_ID}.{DATASET_ID}.{TESTS_TABLE}"
        errors = bq_client.insert_rows_json(table_id, test_cases_to_insert, row_ids=row_ids)
        if errors:
            print(f"    -> BQ Error inserting test cases: {errors[:2]}")
        else:
            print(f"    -> Inserted {len(test_cases_to_insert)} test cases for run {run_id}")


# =========================================================
# 5. Main Extraction Logic
# =========================================================
def _process_run(bq_client, run):
    """Process a single workflow run: fetch jobs, insert into BQ, fetch test artifacts."""
    run_id = run["id"]
    pr_num = extract_pr_number(run)
    branch_name = run.get("head_branch", "Unknown")

    jobs_url = f"https://api.github.com/repos/{REPO}/actions/runs/{run_id}/jobs?per_page=100"
    has_e2e_tests = False
    all_jobs = []

    while jobs_url:
        j_resp = requests.get(jobs_url, headers=HEADERS, timeout=(10, 60))
        if handle_rate_limit(j_resp):
            continue
        if j_resp.status_code != 200:
            raise RuntimeError(f"Failed to fetch jobs for run {run_id}: HTTP {j_resp.status_code}")
        all_jobs.extend(j_resp.json().get("jobs", []))
        jobs_url = j_resp.links.get("next", {}).get("url")

    jobs_to_insert = []
    job_row_ids = []

    for job in all_jobs:
        jobs_to_insert.append(
            {
                "job_id": job["id"],
                "run_id": run_id,
                "run_attempt": run.get("run_attempt", 1),
                "workflow_name": run.get("name", "Unknown"),
                "job_name": job["name"],
                "head_sha": job["head_sha"],
                "branch_name": branch_name,
                "pr_number": pr_num,
                "conclusion": job["conclusion"],
                "started_at": job["started_at"],
                "completed_at": job["completed_at"],
                "runner_group": job.get("runner_group_name"),
            }
        )
        job_row_ids.append(str(job["id"]))

        if "playwright" in job["name"].lower() or "e2e" in job["name"].lower():
            has_e2e_tests = True

    if jobs_to_insert:
        errors = bq_client.insert_rows_json(
            f"{PROJECT_ID}.{DATASET_ID}.{JOBS_TABLE}",
            jobs_to_insert,
            row_ids=job_row_ids,
        )
        if errors:
            raise RuntimeError(f"BQ insert failed for run {run_id}: {errors[:2]}")
        else:
            print(
                f"  -> Inserted {len(jobs_to_insert)} jobs for run {run_id} "
                f"(Branch: {branch_name}, PR: {pr_num})"
            )

    if has_e2e_tests:
        fetch_and_insert_test_artifacts(
            bq_client=bq_client,
            run_id=run_id,
            head_sha=run.get("head_sha"),
            branch_name=branch_name,
            pr_number=pr_num,
            execution_date=run["created_at"],
        )


def sync_ci_data(bq_client):
    """Fetches Runs -> Jobs -> Test Artifacts and streams to BQ."""
    existing_run_ids = get_existing_run_ids(bq_client)
    failed_runs = []

    start_time = datetime.now(timezone.utc) - timedelta(days=DAYS_BACK + 1)
    start_time_str = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"Starting extraction for {REPO} (Since {start_time_str})...")

    runs_url = f"https://api.github.com/repos/{REPO}/actions/runs?created=>{start_time_str}&status=completed&per_page=100"

    while runs_url:
        resp = requests.get(runs_url, headers=HEADERS, timeout=(10, 60))
        if handle_rate_limit(resp):
            continue
        resp.raise_for_status()

        data = resp.json()
        total_count = data.get("total_count", 0)
        runs = data.get("workflow_runs", [])
        if total_count > 1000:
            print(
                f"\nWARNING: {total_count} total runs exceed GitHub's 1,000-result cap. "
                f"Reduce DAYS_BACK to avoid missing data."
            )
        print(f"\nProcessing page with {len(runs)} workflow runs...")

        for run in runs:
            if run["id"] in existing_run_ids:
                print(f"Skipping run {run['id']} (already present in BigQuery)")
                continue

            try:
                _process_run(bq_client, run)
            except Exception as e:
                print(f"  -> Error processing run {run['id']}: {e}; queued for retry")
                failed_runs.append(run)

        runs_url = resp.links.get("next", {}).get("url")

    if failed_runs:
        print(f"\nRetrying {len(failed_runs)} failed run(s)...")
        still_failed = []
        for run in failed_runs:
            try:
                _process_run(bq_client, run)
            except Exception as e:
                print(f"  -> Retry failed for run {run['id']}: {e}")
                still_failed.append(run["id"])

        if still_failed:
            print(
                f"\nSync finished with {len(still_failed)} permanently failed run(s): "
                f"{still_failed}"
            )
            raise SystemExit(1)

    print("\nSync Complete!")


if __name__ == "__main__":
    client = bigquery.Client(project=PROJECT_ID)
    setup_bigquery_tables(client)
    sync_ci_data(client)
