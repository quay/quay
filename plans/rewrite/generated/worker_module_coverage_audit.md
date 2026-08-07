# Worker Module Coverage Audit

Compares worker process entrypoint modules with migration tracker source/module fields.

- worker entrypoint-like modules (`create_gunicorn_worker` or `__main__`): 27
- tracked python source/module entries: 56
- entrypoint modules missing from tracker: 0

## Missing entrypoint modules

- none

## Worker-like non-entrypoint modules (informational)

- `workers/blobuploadcleanupworker/models_pre_oci.py`
- `workers/buildlogsarchiver/models_pre_oci.py`
- `workers/notificationworker/models_pre_oci.py`
- `workers/queueworker.py`
- `workers/repomirrorworker/repo_mirror_model.py`
- `workers/servicekeyworker/models_pre_oci.py`

## Result

- No worker entrypoint coverage gaps detected against migration tracker.
