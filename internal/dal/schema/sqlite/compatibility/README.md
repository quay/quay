# OMR Compatibility SQL

SQL applied by `RunBridge` (see `internal/dal/dbcore/bridge.go`) to bridge a
supported OMR SQLite database onto this binary's target schema.

The accepted source revision is `dbcore.ApprovedOMRSourceVersion`; the
produced revision is `dbcore.TargetVersion`. Both are explicit Go constants —
the accepted source and the applied SQL file are not inferred from directory
contents or an in-file revision comment.
