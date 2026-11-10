# Tenant Control Plane: bounded contexts

## Architecture
- `provisioning`: physical database lifecycle only.
- `data_management`: engine-neutral table and row operations.
- `control_plane`: tenant catalog, database catalog, and audit metadata.
- FastAPI/Jinja presentation depends only on application services.
- SQLite and PostgreSQL are adapters selected by registries at the composition root.

## Run
1. Install Python 3.11+ and ensure `python` is on PATH.
2. Double-click `run.bat`.
3. Open http://127.0.0.1:8000.

SQLite works immediately. PostgreSQL is registered only when `POSTGRES_ADMIN_DSN` is set. The PostgreSQL provisioning account needs `CREATEDB` and `CREATEROLE`. `pg_dump` is required for PostgreSQL backups.

## Logical types
The UI and application use `string`, `integer`, `decimal`, `boolean`, `datetime`, and `binary`. Adapters map these to engine-specific types.

## Current safeguards and limitations
- Every UI-created table has one generated integer primary key.
- Arbitrary SQL is not exposed.
- Identifiers are validated and values use bound parameters.
- SQLite column alteration rebuilds the table transactionally.
- PostgreSQL column alteration uses native `ALTER TABLE`.
- PostgreSQL credentials are used during provisioning but this starter does not include a production secret store. Configure `POSTGRES_ADMIN_DSN` securely and do not expose the app outside localhost.
- No authentication is included; bind to `127.0.0.1`.

## Observability foundation
- Structured JSON diagnostic log: `logs/control-plane.jsonl`
- Structured audit log: `logs/audit.jsonl`
- 10 MB rotating files with 10 retained backups
- Correlation IDs accepted and returned through `X-Correlation-ID`
- `GET /health/live` for process liveness
- `GET /health/ready` for catalog and adapter readiness
- `GET /metrics` for Prometheus text-format counters and duration sums/counts
- Passwords, connection strings, request bodies, and imported row values are not written to logs

Metrics are intentionally in-memory in this increment, so counters reset when the process restarts. The `MetricsRecorder` and `EventRecorder` ports allow later replacement with OpenTelemetry, Prometheus client, Azure Monitor, or another backend without changing application services.

## Observability GUI
Open `http://127.0.0.1:8000/observability`. The page shows readiness, configured adapters, recent request and audit events, error count, HTTP status summary, correlation IDs, and raw Prometheus metrics. It reads at most 500 recent lines from each JSONL log and refreshes every 15 seconds.

## Observability reliability fix
The metrics label renderer was corrected to process label key/value pairs rather than dictionary keys. The HTTP instrumentation now uses pure ASGI middleware instead of Starlette `BaseHTTPMiddleware`, preventing downstream exceptions from being obscured by `ExceptionGroup` wrappers. Automated endpoint tests cover `/`, `/health/live`, `/health/ready`, `/metrics`, and `/observability`.

## Increment 2: File Inbox
Set `CONTROL_PLANE_INBOX` to configure the physical inbox root; the default is `<application>/inbox`. Set `CONTROL_PLANE_MAX_UPLOAD_BYTES` to change the 100 MB limit. Uploads stream in 1 MB chunks to `staging`, are hashed with SHA-256, and are atomically moved into content-addressed `objects/<2>/<2>/<sha256>` paths. Supported types are CSV and XLSX.

Duplicate decisions: same name + same contents returns the existing file; different name + same contents requires explicit alias approval and stores no duplicate bytes; same name + different contents is rejected as a name conflict and must be renamed; new name + new contents is accepted. Open `/inbox` for the listing and upload GUI.

## Configuration files
All editable configuration is under `config/`. `config/system.toml` controls the web server host, port, log level, and reload setting. `run.bat` no longer contains host or port; it invokes `launcher.py`, which reads this file. `config/inbox.toml` contains the complete File Inbox configuration: root directory, metadata database, maximum upload bytes, streaming chunk size, allowed extensions, and whether the storage reference is shown.

The inbox is system-wide and files may be uploaded before tenants or databases exist. They are not orphaned; `inbox.db` owns their metadata and the content-addressed object store owns their bytes. A tenant/database relationship is intentionally deferred until a future import job selects an inbox file and target database. The metadata page now reports whether the physical object exists and provides a Verify button that recomputes SHA-256 from disk.

## Increment 3: File inspection
Open an Inbox file metadata page and select **Inspect tabular contents**. CSV files are inspected immediately. XLSX files expose worksheet selection when multiple sheets are present. The report verifies SHA-256, normalizes headers, infers engine-neutral logical types, previews up to 100 rows, profiles nullability, and reports validation errors/warnings. Settings are centralized in `config/inspection.toml`. Machine-readable endpoints are `GET /api/inbox/files/{id}/datasets` and `GET /api/inbox/files/{id}/inspection?dataset=...`. Inspection does not create tables or import rows.

## Increment 3.1 and 4
Physical inspection preserves blank and hidden rows with original source-row numbers. Users confirm document-header, column-header, and data ranges before import. Column mappings can be saved as recurring statement templates; the auto-processing permission checkbox defaults to enabled. Templates are auto-detected using extension plus normalized header signature. Creating a table uses a generated staging table, batched inserts, and an atomic rename. Import jobs and templates are stored in `imports.db` and shown at `/imports/history`.
