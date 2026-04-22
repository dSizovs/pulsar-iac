# Pulsar-Relay Failure Testing

Stress testing of the Galaxy → pulsar-relay → Pulsar → Slurm pipeline under failure conditions.

## Setup

- **Galaxy VM**: `141.70.30.222` (university network), running Galaxy 26.0
- **pulsar-relay**: `192.52.32.144` (bw-cloud public VM), running `pulsar-relay` via systemd
- **Pulsar**: NEMO login2 (`132.230.245.12`), running `pulsar-main` with Slurm backend
- **File transfers**: Pulsar ↔ Galaxy direct HTTP via SSH reverse tunnel (`-R 8080:192.168.2.6:8080`)

### Scripts

All scripts live in `scripts/` and were run on the Galaxy VM.

| Script | Purpose |
|---|---|
| `new_stress_history.py` | Creates a fresh Galaxy history and copies a known-good tabular input dataset into it. Prints the new `HISTORY_ID` and `INPUT_DATASET_ID` to paste into the other scripts. |
| `submit_jobs.py` | Submits N ChangeCase jobs to a given history via the Galaxy API. Writes a JSON log to `/tmp/submit_<scenario>_<timestamp>.json`. |
| `monitor_jobs.py` | Polls Galaxy job states every 2s, scoped to a single history. Writes a CSV log to `/tmp/monitor_<scenario>_<timestamp>.csv`. Also probes relay TCP health. |

### Baseline

Before failure testing, a clean baseline run was performed:

```
python3 monitor_jobs.py --scenario baseline --history <id>
python3 submit_jobs.py  --scenario baseline --count 100
```

Result: 100/100 jobs completed at ~1 job/4 seconds with no errors. One transient relay DOWN blip (2 seconds) had no impact on job completion.

---

## Scenario 1 — Pulsar Goes Down

### Method

1. Submit 100 jobs
2. Once `active > 50`, kill Pulsar: `pkill -f pulsar-main`
3. Wait 60 seconds
4. Restart Pulsar: `nohup pulsar-main --app_conf_path config/app.yml > pulsar.log 2>&1 &`

### Observations

- Jobs froze immediately in `new`/`queued` state when Pulsar died
- Galaxy has **no timeout** for jobs waiting to be dispatched — it waits indefinitely
- Jobs already completed before Pulsar died: ✅ unaffected
- After Pulsar restart: jobs did **not** auto-resume
- Galaxy was stuck polling for status updates from a `queued` job that Pulsar had no memory of
- Manually deleting the stuck `queued` job via the API unblocked the remaining `new` jobs
- The `resubmit` rule in `job_conf.yml` fired correctly (3 retries, 30s delay) but ultimately gave up → jobs moved to `paused`

### Key Finding

> **Pulsar going down causes jobs to freeze. Recovery is not automatic. A stuck `queued` job can block all subsequent `new` jobs from being dispatched. Manual intervention required.**

### Recovery Steps

```bash
# Find and delete stuck queued job
curl -s "http://localhost:8080/api/jobs?state=queued&limit=10" \
  -H "x-api-key: <key>" | python3 -c "
import sys, json
for j in json.load(sys.stdin): print(j['id'], j['state'])"

curl -X DELETE "http://localhost:8080/api/jobs/<job_id>" \
  -H "x-api-key: <key>"

# Resume paused jobs
curl -s "http://localhost:8080/api/jobs?state=paused&limit=200" \
  -H "x-api-key: <key>" | python3 -c "
import sys, json, subprocess
for j in json.load(sys.stdin):
    subprocess.run(['curl','-s','-X','PUT',
        f'http://localhost:8080/api/jobs/{j[\"id\"]}/resume',
        '-H','x-api-key: <key>'], capture_output=True)"
```

### Production Recommendation

- Add a watchdog script that detects stuck `queued` jobs and auto-resumes `paused` jobs when Pulsar comes back online
- Configure Galaxy job resubmission rules appropriately for production workloads

---

## Scenario 2 — Relay Goes Down

### Method

1. Submit 100 jobs
2. Once `active > 50`, stop relay: `sudo systemctl stop pulsar-relay`
3. Wait 60 seconds
4. Restart relay: `sudo systemctl start pulsar-relay`

### Observations

Monitor output at relay stop:
```
16:58:49  galaxy=OK  relay=OK   active=94  paused=0  ok=10
16:58:51  galaxy=OK  relay=DOWN active=94  paused=0  ok=10   ← relay stopped
...
16:59:19  galaxy=OK  relay=OK   active=94  paused=0  ok=10   ← relay back
16:59:21  galaxy=OK  relay=OK   active=93  paused=0  ok=11   ← jobs resuming
```

- Jobs froze immediately when relay went down
- Both Galaxy and Pulsar lost connection and retried continuously
- When relay restarted, both **automatically re-authenticated** (JWT login) within seconds
- Jobs resumed processing **automatically** with no manual intervention
- No jobs were lost

### Key Finding

> **Relay going down freezes jobs but recovery is fully automatic. Both Galaxy and Pulsar re-authenticate and resume within seconds of the relay coming back. Zero jobs lost.**

### Important Caveat

The relay uses **in-memory storage** by default. If the relay process is killed (not gracefully stopped), any in-flight messages are lost and jobs may need to be resubmitted. 

**Production recommendation: configure Valkey persistent storage:**

```ini
# /etc/systemd/system/pulsar-relay.service
Environment="PULSAR_STORAGE_BACKEND=valkey"
Environment="PULSAR_VALKEY_HOST=localhost"
```

With Valkey, relay restart would preserve all messages and tokens, making recovery seamless even after a crash.

---

## Scenario 3 — Galaxy Goes Down

### Method

1. Submit 100 jobs
2. Once `active > 50`, kill Galaxy: `Ctrl+C` on `sh run.sh`
3. Wait 30 seconds
4. Restart Galaxy: `sh run.sh`

### Observations

Monitor output:
```
10:25:07  galaxy=OK    active=90  paused=0  ok=10
10:25:12  galaxy=DOWN  active=0   paused=0  ok=0    ← Galaxy down
...
10:26:03  galaxy=OK    active=90  paused=0  ok=10   ← Galaxy back, jobs recovered
10:26:08  galaxy=OK    active=90  paused=0  ok=10
10:26:13  galaxy=OK    active=89  paused=0  ok=11   ← jobs resuming
```

- Galaxy down = API immediately unreachable (monitor shows `galaxy=DOWN`)
- On restart, Galaxy **automatically recovered all pending jobs from the SQLite database**
- Jobs that had already been dispatched to Pulsar continued running on NEMO uninterrupted
- Jobs resumed processing automatically after restart

### Edge Case: Unassigned Jobs

If Galaxy crashes during job submission (between writing the job to DB and assigning it to a handler), jobs can be left with `handler = NULL`. These jobs are **not** automatically picked up after restart.

```bash
# Detect unassigned jobs
curl -s "http://localhost:8080/api/jobs?state=new&limit=200" \
  -H "x-api-key: <key>" | python3 -c "
import sys, json
jobs = json.load(sys.stdin)
unassigned = [j for j in jobs if j.get('handler') is None]
print(f'{len(unassigned)} unassigned jobs')"
```

Fix: update the handler assignment directly in the SQLite database:
```bash
sqlite3 ~/galaxy/database/galaxy.sqlite \
  "UPDATE job SET handler='main.1' WHERE state='new' AND handler IS NULL;"
```

### Key Finding

> **Galaxy restart results in full automatic recovery from the database. Jobs resume processing without manual intervention. Exception: jobs submitted during the crash window may have NULL handler and require manual DB intervention.**

---

## Summary

| Scenario | Jobs frozen? | Auto-recovery? | Jobs lost? | Manual action needed? |
|---|---|---|---|---|
| Pulsar down | ✅ Yes | ❌ No | ❌ No (paused) | Resume paused jobs, delete stuck queued job |
| Relay down | ✅ Yes | ✅ Yes | ❌ No | None (with graceful restart) |
| Galaxy down | ✅ Yes | ✅ Yes | ❌ No* | None (*unless crash during submission) |

## Production Recommendations

1. **Valkey storage for relay** — prevents message loss on relay restart/crash
2. **Watchdog for paused jobs** — auto-resume paused jobs when Pulsar comes back
3. **Galaxy job timeout** — configure a timeout for running jobs so they don't wait indefinitely if Pulsar disappears without reporting
4. **Pulsar systemd service on NEMO** — currently run manually; should be a systemd service for auto-restart
5. **Persistent relay** — already done via systemd on bw-cloud
