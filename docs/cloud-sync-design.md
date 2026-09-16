# Design: local-to-cloud sync for KT model training data

Status: **DEFERRED — not implemented.** Written 2026-09-17, validated from a
draft an Antigravity session produced. Do not build this until the trigger
condition below is actually met — see "Why deferred."

## Goal

Once more than one student (the real student's friends) is running her own
local instance, aggregate anonymized practice attempts from all of them into
one central store, so `research/synthetic_jee_kt/` has real multi-student data
to fit BKT/LKT/PFA against instead of synthetic-only data.

## Why deferred

Right now there is one real student and zero friends onboarded. This design
needs: a Supabase project, RLS policies, an env-var-gated sync path, two new
local columns, and new tests — real infrastructure for a population that
doesn't exist yet. Until friends are actually using their own instances, use
the simpler path already agreed: each instance can export its own
`attempts`/`concepts` as flat, anonymized JSONL (stdlib `json`, no new
tooling) and the file gets passed to the maintainer manually. Build *this*
doc's design only when manual file-passing between a handful of installs
becomes the actual bottleneck — not before.

**Trigger to revisit:** more than ~3-4 active friend installs, or manual
JSONL hand-off happening often enough to be annoying.

## Corrections to the original draft

The original brief (reproduced in `docs/decisions.md`'s log for
2026-09-17) had three problems that must be fixed before this ships, not
left as follow-ups:

### 1. Open INSERT policy + public PyPI package = open write sink

The draft's RLS policy is `FOR INSERT TO anon WITH CHECK (true)`. Combined
with the package being published to public PyPI (separately in progress —
see `docs/production-readiness-notes.md` item 2), the anon key ships inside
every install anyone in the world can `pip install`. An open anon-insert
policy with no validation means anyone who finds the package can point
unlimited garbage traffic at `student_interactions`, not just the intended
handful of friends.

**Fix:** put a Supabase Edge Function in front of the insert instead of a
raw table policy. It should reject anything that doesn't match the expected
shape (known `subject`/`result` enums, timestamp in a sane range, payload
size cap, batch size cap matching the client's `LIMIT 250`). The RLS policy
becomes `TO service_role` only; clients call the Edge Function, not the
table directly.

### 2. No idempotency — double-counted rows on partial failure

The draft POSTs a batch, then updates `synced = 1` locally after a 200/201.
If the process dies or the network drops between Supabase accepting the
rows and the local `UPDATE` committing, the same batch gets re-sent and
double-inserted next sync — silently corrupting the training set with
duplicate interactions.

**Fix:** give each local attempt a stable client-generated id (e.g. a UUID
column on `attempts`, or reuse the existing `attempts.id` prefixed with the
student UUID) and add a `UNIQUE (student_id, client_attempt_id)` constraint
on `student_interactions`. Insert with `ON CONFLICT DO NOTHING` (Supabase
REST: `Prefer: resolution=ignore-duplicates`) so a re-sent batch is a no-op
instead of a duplicate.

### 3. Ambiguous timestamp unit

The draft's column comment says "Unix epoch ms or seconds from client" —
picking either is fine, leaving it ambiguous is not. KT models depend on
correct per-student chronological ordering; if two installs disagree on the
unit, cross-student ordering (though each student's own sequence stays
internally consistent either way) and any cross-student time-based
features silently break with no error.

**Fix:** pin it explicitly. Use milliseconds — matches `attempts.created_at`
in the existing local schema (`src/db.py`), so the client sends the same
value it already stores, no conversion step to get wrong.

## Revised design (apply corrections above to the original draft)

### Supabase schema

```sql
CREATE TABLE student_interactions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    student_id UUID NOT NULL,
    client_attempt_id TEXT NOT NULL,      -- stable per-attempt id from the client, for dedup
    subject TEXT NOT NULL,
    concept_name TEXT NOT NULL,
    result TEXT NOT NULL CHECK (result IN ('correct', 'wrong', 'unattempted')),
    time_seconds INTEGER,
    error_type TEXT,
    attempt_timestamp_ms BIGINT NOT NULL, -- epoch milliseconds, matches local created_at
    ingested_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (student_id, client_attempt_id)
);

CREATE INDEX idx_kt_student_seq ON student_interactions (student_id, attempt_timestamp_ms ASC);
CREATE INDEX idx_kt_concept ON student_interactions (concept_name);

ALTER TABLE student_interactions ENABLE ROW LEVEL SECURITY;
-- No client-facing INSERT policy. Writes only via the validating Edge
-- Function below, using the service_role key (server-side only, never
-- shipped to clients).
```

### Edge Function (`sync-ingest`), not a raw table policy

Validates before writing:
- `student_id` is a well-formed UUID.
- `result` is one of the three allowed values.
- `subject`/`concept_name` are non-empty strings under a length cap.
- `attempt_timestamp_ms` is a plausible epoch-ms value (not in the future,
  not before the project existed).
- Batch size <= 250 (matches client `LIMIT`).
- Inserts with `ON CONFLICT (student_id, client_attempt_id) DO NOTHING`.

The client posts to the Edge Function URL with the anon key (identifies the
caller as a legitimate client of the function, not as direct table access);
the function itself holds the service_role key server-side to perform the
actual insert after validation passes.

### Local changes (`src/db.py`)

- Add `synced INTEGER NOT NULL DEFAULT 0` to `attempts` (migration guard:
  `ALTER TABLE ... ADD COLUMN` wrapped in a check against
  `PRAGMA table_info`, same pattern as any other additive migration in
  `init_db`).
- Add `student_uuid TEXT` to the singleton `student_profile` row,
  generated once via `uuid.uuid4().hex` on first startup if null.
- `client_attempt_id` sent to Supabase = `f"{student_uuid}:{attempt.id}"`
  (stable, no new local column needed — local `attempts.id` is already a
  stable per-install primary key).

### `src/cloud_sync.py`

Same shape as the original draft (`sync_unpushed_attempts(conn)`, stdlib
`urllib.request` only, graceful no-op when `JEE_SUPABASE_URL`/
`JEE_SUPABASE_KEY` are unset, 5s timeout, catches and logs network errors
without raising) — posts to the Edge Function URL instead of the table's
REST endpoint, sends `attempt_timestamp_ms` (not `attempt_timestamp`), and
includes `client_attempt_id` per row.

Loop the `LIMIT 250` fetch instead of a single call, so a long-offline
install catches up fully in one `end_study_session` call rather than
draining 250 rows per session:

```python
def sync_unpushed_attempts(conn: sqlite3.Connection) -> int:
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        return 0
    total = 0
    while True:
        n = _sync_one_batch(conn)
        if n == 0:
            break
        total += n
    return total
```

### Consent

Sync is off by default (no env vars set = no network call, ever). Before
any friend sets `JEE_SUPABASE_URL`/`JEE_SUPABASE_KEY`, `docs/setup.md` must
say plainly what gets sent (anonymized subject/concept/result/timing, no
name/email) and that it's opt-in — not just implied by "the env var isn't
set by default."

## Implementation checklist (when the trigger condition is met)

- [ ] `synced` column on `attempts`, migration-guarded.
- [ ] `student_uuid` on `student_profile`, auto-generated if null.
- [ ] Supabase table + indexes + `sync-ingest` Edge Function (validation +
      `ON CONFLICT DO NOTHING`), RLS with no direct client INSERT policy.
- [ ] `src/cloud_sync.py`: batched loop, epoch-ms timestamp,
      `client_attempt_id` dedup key, mockable HTTP tests.
- [ ] Hook into `src/tools/end_study_session.py` after the local profile
      update.
- [ ] `tests/test_cloud_sync.py`: unsynced rows get selected and marked
      `synced = 1`; offline/timeout errors caught, don't raise or corrupt
      local state; re-sending an already-synced batch is a no-op (dedup
      test).
- [ ] `docs/setup.md` gets an opt-in consent paragraph before either env
      var is documented as something a friend should set.
