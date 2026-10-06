# Warm-control operations

Normal application traffic stays Browser → Vercel → Render → Supabase. The separate
`infrastructure/warm-control` Worker does not proxy application traffic.

## Configuration

| Setting | Value / location |
| --- | --- |
| Worker | `tracelens-warm-control` |
| Public activation | `https://tracelens-warm-control.dumpydon.workers.dev/api/warm/activate` |
| KV namespace/binding | `TRACELENS_STATE` |
| KV key | `render_warm_until` (decimal UTC epoch milliseconds) |
| Render | `https://tracelens-uh8e.onrender.com` (`RENDER_API_BASE_URL` in Wrangler) |
| Browser origin | `https://tracelens-seven.vercel.app` (`FRONTEND_ORIGIN` in Wrangler) |
| Vercel public variable | `NEXT_PUBLIC_WARM_CONTROL_URL=https://tracelens-warm-control.dumpydon.workers.dev` |
| Dedicated secret | `TRACELENS_KEEPALIVE_SECRET`, stored only as a Worker secret and Render environment variable |

`POST /api/warm/activate` ignores all client expiry/duration values. Missing, invalid or
expired KV state creates `now + 3 hours`; active state returns the same ISO timestamp and
`created: false` without a write. KV is eventually consistent, so simultaneous cold
activations in different locations can race; this accepted portfolio tradeoff is not a
strict distributed lock. No cookies, browser storage, or PostgreSQL lease rows are used.

Browser activation runs asynchronously on the persistent runtime provider's mount, only
for a production build with a non-local API and a configured public Worker URL. It has a
five-second timeout, no credential header, and no user-visible failure. Duplicate effects,
tabs and refreshes are harmless under the server lease rule. Route changes do not reactivate
the persistent provider. CORS permits only the configured production origin; origin-less
operational callers may also POST. Other routes and methods are rejected.

## Scheduled operations

Wrangler owns both UTC triggers:

* `*/10 * * * *`: if `now < warm_until`, send one `GET /health` (15-second timeout).
  Otherwise skip. No lease is created or extended by this trigger.
* `30 3 * * *`: at 09:00 IST, ensure `max(existing expiry, today's 06:30 UTC/noon IST)`.
  A visit at 10:30 IST reuses noon; a pre-existing 13:00 lease remains 13:00. Late events
  arriving after their anchored noon are skipped. The overlapping ten-minute event at
  03:30 UTC yields to the daily handler.

The daily handler immediately sends `POST /internal/maintenance/heartbeat` with the
dedicated bearer token. This request also wakes Render. Up to three attempts within one
90-second deadline, with ten seconds between transient failures, allow a cold-start 503.
Auth/configuration failures are not retried. If the secret is missing, a normal health
request still attempts to wake Render and a safe configuration warning is logged. KV
failure does not prevent the daily database attempt. DB failure never changes a valid lease.

The existing `/health` response is static and **does not query the database**. The protected
heartbeat calls `Database.heartbeat()` → `Database.connect()` → existing psycopg pool →
`SELECT 1 AS alive` → `fetchone()` on every request; only then returns
`{status: "ok", database: "postgresql", checked_at: "..."}`. SQLite is supported for local
tests but is not accepted as production PostgreSQL proof by the Worker. Missing secrets
disable the endpoint; missing/incorrect bearer tokens return 401; database errors return
a generic 503. No user data or exception/credential contents are logged.

These request handlers do not call OpenAI, LangGraph, RAG, embeddings or evaluations.
Render's pre-existing production startup still initializes its vector store; if that store
is empty, its existing initialization can ingest embeddings. Warming does not add or
change that startup behavior, and a heartbeat alone is not proof of zero startup AI traffic.
The heartbeat is genuine lightweight PostgreSQL activity intended to keep the existing
project exercised; it is not a contractual guarantee that Supabase cannot pause.

## Validation / deployment

Worker tooling requires Node 22.12+ and is separate from the frontend:

```bash
cd infrastructure/warm-control
npm ci
npm test
npm run typecheck
npm run dry-run
npm run deploy
```

Wrangler contains the dedicated account, KV ID, endpoint and both triggers. No secrets are
in that file. For a fresh account, create `TRACELENS_STATE` with `wrangler kv namespace create
TRACELENS_STATE`, update only the namespace ID, and configure the same freshly generated
token in Render and `wrangler secret put TRACELENS_KEEPALIVE_SECRET`. Enter it interactively
or through stdin, never as a command argument. Existing DayPilot/Jevon resources are separate.

The current Worker/KV and public Vercel variable can be provisioned independently. The
heartbeat route and browser activation code require the repository's normal development
branch → main release. Do not change Render's deployment branch or auto-merge merely to
validate them. After that release:

1. Confirm Vercel and Render deployed the expected commit.
2. POST activation twice with the production Origin; compare exact `warm_until` values.
3. Inspect Worker schedules/bindings, and observe a real scheduled invocation in
   `wrangler tail tracelens-warm-control --format json`.
4. Verify the authenticated heartbeat returns `database: "postgresql"` and a fresh
   `checked_at`; inspect the code/DB statistics for the real SELECT, not cached status.
5. Compare incident/evaluation/checkpoint counts before and after. Do not create demo data
   or run paid evaluations to validate warming.

Before that release, the production heartbeat URL can return 404. Treat this as pending
deployment, not successful database proof. Cron failure, paused Supabase, or Worker/KV
unavailability must never prevent the regular Vercel/Render app from working.
