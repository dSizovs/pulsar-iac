#!/usr/bin/env python3
"""
Failure-test monitor for Galaxy -> pulsar-relay -> Pulsar.

Logs, every POLL_INTERVAL seconds:
  - Galaxy-side job state counts (history-scoped, so counts don't plateau)
  - Galaxy API reachability + latency
  - pulsar-relay TCP reachability
  - Pulsar TCP reachability (via relay's upstream, if you expose it; else skipped)

Usage:
  python3 monitor_jobs.py --scenario baseline
  python3 monitor_jobs.py --scenario kill_relay
  python3 monitor_jobs.py --scenario kill_pulsar --history 1cd8e2f6b131e891
"""
import argparse
import csv
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

GALAXY_URL = "http://localhost:8080"
API_KEY = "158f39b893d924af6af674b6ce7b3efb"
DEFAULT_HISTORY = "2d9035b3fc152403"

# Component endpoints to probe for liveness (TCP connect only, no auth needed)
RELAY_HOST = "192.52.32.144"
RELAY_PORT = 9000
# Pulsar on NEMO login2 is not directly reachable from Galaxy VM in your topology
# (that's the whole point of the relay), so we skip a direct Pulsar probe here.
# If you want Pulsar liveness, SSH-exec `pgrep -f pulsar-main` on NEMO from a
# sidecar script, or have the relay expose an upstream-health endpoint.

# All Galaxy job states worth tracking. 'paused' is the important one for
# Scenario 1 (Pulsar down) — do NOT drop it.
JOB_STATES = [
    "new", "waiting", "queued", "running",
    "paused", "stopped",
    "ok", "error", "deleted", "upload",
]

HEADERS = {"x-api-key": API_KEY}


def tcp_reachable(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, socket.timeout):
        return False


def get_job_states(history_id: str) -> tuple[dict, bool, float]:
    """Return (state_counts, galaxy_ok, latency_ms).

    Scoped to a single history so counts reflect *this* test run, not the
    accumulated lifetime of the Galaxy instance.
    """
    counts = {s: 0 for s in JOB_STATES}
    t0 = time.monotonic()
    try:
        # One call, filter client-side -> atomic snapshot, no per-state races.
        r = requests.get(
            f"{GALAXY_URL}/api/jobs",
            params={"history_id": history_id, "limit": 1000},
            headers=HEADERS,
            timeout=5,
        )
        latency_ms = (time.monotonic() - t0) * 1000
        if r.status_code != 200:
            return counts, False, latency_ms
        for job in r.json():
            state = job.get("state", "unknown")
            if state in counts:
                counts[state] += 1
            else:
                counts.setdefault(state, 0)
                counts[state] += 1
        return counts, True, latency_ms
    except requests.RequestException:
        return counts, False, (time.monotonic() - t0) * 1000


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", required=True,
                    help="Tag for this run (e.g. kill_relay, kill_pulsar, baseline)")
    ap.add_argument("--history", default=DEFAULT_HISTORY,
                    help="Galaxy history ID to scope jobs to")
    ap.add_argument("--interval", type=float, default=2.0,
                    help="Poll interval in seconds (default 2.0)")
    ap.add_argument("--logdir", default="/tmp", help="Where to write CSV logs")
    args = ap.parse_args()

    ts_tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = Path(args.logdir) / f"monitor_{args.scenario}_{ts_tag}.csv"

    fieldnames = [
        "timestamp", "scenario",
        *JOB_STATES,
        "galaxy_ok", "galaxy_latency_ms",
        "relay_ok",
    ]

    print(f"[monitor] scenario={args.scenario} history={args.history}")
    print(f"[monitor] logging to {log_path}")
    print(f"[monitor] poll every {args.interval}s — Ctrl-C to stop")

    with log_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        f.flush()

        try:
            while True:
                now = datetime.now(timezone.utc).isoformat()
                counts, galaxy_ok, latency = get_job_states(args.history)
                relay_ok = tcp_reachable(RELAY_HOST, RELAY_PORT)

                row = {
                    "timestamp": now,
                    "scenario": args.scenario,
                    **{s: counts.get(s, 0) for s in JOB_STATES},
                    "galaxy_ok": galaxy_ok,
                    "galaxy_latency_ms": round(latency, 1),
                    "relay_ok": relay_ok,
                }
                w.writerow(row)
                f.flush()

                # Compact stdout summary
                active = counts["new"] + counts["queued"] + counts["running"]
                print(
                    f"{now}  galaxy={'OK' if galaxy_ok else 'DOWN':4}  "
                    f"relay={'OK' if relay_ok else 'DOWN':4}  "
                    f"active={active:3}  paused={counts['paused']:3}  "
                    f"ok={counts['ok']:3}  err={counts['error']:3}"
                )

                time.sleep(args.interval)
        except KeyboardInterrupt:
            print(f"\n[monitor] stopped. log: {log_path}")
            return 0


if __name__ == "__main__":
    sys.exit(main())
