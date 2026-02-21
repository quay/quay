# Non-Blueprint Route Inventory

Routes registered via `app.add_url_rule` outside standard endpoint blueprint/resource scanning.

| Route ID | Method | Path | Source file | Auth mode | Notes |
|---|---|---|---|---|---|
| `ROUTE-0411` | `GET` | `/userfiles/<regex("[0-9a-zA-Z-]+"):file_id>` | `data/userfiles.py` | `anon-allowed` | supplemental inventory: non-blueprint app.add_url_rule route; security relies on file-id handling/signed URL flow |
| `ROUTE-0412` | `PUT` | `/userfiles/<regex("[0-9a-zA-Z-]+"):file_id>` | `data/userfiles.py` | `anon-allowed` | supplemental inventory: non-blueprint app.add_url_rule route; security relies on file-id handling/signed URL flow |
| `ROUTE-0413` | `GET` | `/_storage_proxy_auth` | `storage/downloadproxy.py` | `storage-proxy-jwt` | supplemental inventory: non-blueprint app.add_url_rule route; validates storage proxy JWT from headers |
