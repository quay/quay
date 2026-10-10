# Operational Tooling Inventory

Python CLI/admin scripts discovered under `tools/` and `util/` requiring migration or retirement decisions.

- scripts: 16

| Script | Argparse | Main guard | Category |
|---|---|---|---|
| `tools/emailinvoice.py` | `true` | `false` | `manual-cli` |
| `tools/generatekeypair.py` | `true` | `false` | `crypto-config` |
| `tools/invoices.py` | `false` | `true` | `manual-cli` |
| `tools/migratebranchregex.py` | `false` | `true` | `data-admin` |
| `tools/renameuser.py` | `true` | `false` | `data-admin` |
| `tools/renderinvoice.py` | `true` | `false` | `manual-cli` |
| `tools/sendconfirmemail.py` | `true` | `false` | `email-ops` |
| `tools/sendresetemail.py` | `true` | `false` | `email-ops` |
| `util/backfillreplication.py` | `false` | `true` | `manual-cli` |
| `util/config/configdocs/configdoc.py` | `false` | `true` | `manual-cli` |
| `util/disableabuser.py` | `true` | `false` | `manual-cli` |
| `util/fixuseradmin.py` | `true` | `true` | `data-admin` |
| `util/generatepresharedkey.py` | `true` | `true` | `crypto-config` |
| `util/migrate/delete_access_tokens.py` | `false` | `true` | `manual-cli` |
| `util/removelocation.py` | `true` | `true` | `data-admin` |
| `util/verifyplacements.py` | `false` | `true` | `manual-cli` |
