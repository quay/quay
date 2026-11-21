# HTTP Surface Coverage Audit

Compare runtime route registration sources with `route_migration_tracker.csv`.

- tracker route rows: 413
- tracker source files: 55
- registration source files scanned: 25
- registration files missing from tracker file column: 1
- tracker files without local registration pattern match: 31

## Registration files missing from tracker

- `endpoints/api/__init__.py` (call:add_resource) -> registration helper using add_resource; resource modules are tracked individually

## Tracker files without direct registration pattern

- `endpoints/api/appspecifictokens.py`
- `endpoints/api/billing.py`
- `endpoints/api/build.py`
- `endpoints/api/capabilities.py`
- `endpoints/api/discovery.py`
- `endpoints/api/error.py`
- `endpoints/api/globalmessages.py`
- `endpoints/api/immutability_policy.py`
- `endpoints/api/logs.py`
- `endpoints/api/manifest.py`
- `endpoints/api/mirror.py`
- `endpoints/api/namespacequota.py`
- `endpoints/api/org_mirror.py`
- `endpoints/api/organization.py`
- `endpoints/api/permission.py`
- `endpoints/api/policy.py`
- `endpoints/api/prototype.py`
- `endpoints/api/repoemail.py`
- `endpoints/api/repository.py`
- `endpoints/api/repositorynotification.py`
- `endpoints/api/repotoken.py`
- `endpoints/api/robot.py`
- `endpoints/api/search.py`
- `endpoints/api/secscan.py`
- `endpoints/api/signing.py`
- `endpoints/api/suconfig.py`
- `endpoints/api/superuser.py`
- `endpoints/api/tag.py`
- `endpoints/api/team.py`
- `endpoints/api/trigger.py`
- `endpoints/api/user.py`

## Result

- No unexpected HTTP registration gaps detected in migration tracker.
