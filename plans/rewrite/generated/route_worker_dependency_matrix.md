# Route/Queue/Worker Dependency Matrix

Maps queue producers in endpoint files to queue consumers in worker processes for cutover sequencing.

- queue rows: 9

| Queue | Producer route files | Producer route rows | Producer waves | Consumer programs | Consumer waves | Constraint |
|---|---|---:|---|---|---|---|
| `chunk_cleanup` | - | 0 | - | `chunkcleanupworker` | `P2` | no direct route->worker dependency discovered from static file mapping |
| `imagestoragereplication` | - | 0 | - | `storagereplication` | `P2` | no direct route->worker dependency discovered from static file mapping |
| `proxycacheblob` | - | 0 | - | `proxycacheblobworker` | `P2` | no direct route->worker dependency discovered from static file mapping |
| `dockerfilebuild` | - | 0 | - | `builder` | `P5` | no direct route->worker dependency discovered from static file mapping |
| `notification` | `endpoints/secscan.py` | 3 | `A3` | `notificationworker`, `securityscanningnotificationworker` | `P2` | route cutover may advance before worker cutover only with mixed-mode queue compatibility tests |
| `secscanv4` | `endpoints/secscan.py` | 3 | `A3` | `securityscanningnotificationworker` | `P2` | route cutover may advance before worker cutover only with mixed-mode queue compatibility tests |
| `exportactionlogs` | - | 0 | - | `exportactionlogsworker` | `P2` | no direct route->worker dependency discovered from static file mapping |
| `repositorygc` | - | 0 | - | `repositorygcworker` | `P4` | no direct route->worker dependency discovered from static file mapping |
| `namespacegc` | - | 0 | - | `namespacegcworker` | `P4` | no direct route->worker dependency discovered from static file mapping |
