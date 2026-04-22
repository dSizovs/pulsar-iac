"""
Submit N identical ChangeCase jobs for failure-testing.

Usage:
  python3 submit_jobs.py --scenario kill_relay
  python3 submit_jobs.py --scenario baseline --count 100
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

GALAXY_URL = "http://localhost:8080"
API_KEY = "158f39b893d924af6af674b6ce7b3efb"

# update after running new_stress_history.py:
HISTORY_ID = "2d9035b3fc152403"
INPUT_DATASET_ID = "95fa410213cac0ea"

HEADERS = {"x-api-key": API_KEY, "Content-Type": "application/json"}


def submit_one(index: int) -> dict:
    payload = {
        "tool_id": "ChangeCase",
        "history_id": HISTORY_ID,
      "inputs": {
          "input|src": "hda",
          "input|id": INPUT_DATASET_ID,
          "casechange": "up",
          "col": "c1",
      },
    }
    t0 = time.monotonic()
    record = {
        "index": index,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "job_id": None,
        "http_status": None,
        "latency_ms": None,
        "error": None,
    }
    try:
        r = requests.post(f"{GALAXY_URL}/api/tools",
                          headers=HEADERS, json=payload, timeout=10)
        record["latency_ms"] = round((time.monotonic() - t0) * 1000, 1)
        record["http_status"] = r.status_code
        if r.status_code == 200:
            try:
                record["job_id"] = r.json()["jobs"][0]["id"]
            except (KeyError, IndexError, ValueError) as e:
                record["error"] = f"unexpected response shape: {e}"
        else:
            record["error"] = r.text[:200]
    except requests.RequestException as e:
        record["latency_ms"] = round((time.monotonic() - t0) * 1000, 1)
        record["error"] = f"{type(e).__name__}: {e}"
    return record


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", required=True,
                    help="Tag for this batch (matches monitor_jobs.py)")
    ap.add_argument("--count", type=int, default=100)
    ap.add_argument("--pace", type=float, default=0.1,
                    help="Sleep between submissions in seconds (default 0.1)")
    ap.add_argument("--outdir", default="/tmp")
    args = ap.parse_args()

    ts_tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = Path(args.outdir) / f"submit_{args.scenario}_{ts_tag}.json"

    print(f"[submit] scenario={args.scenario}  count={args.count}  pace={args.pace}s")
    print(f"[submit] history={HISTORY_ID}  dataset={INPUT_DATASET_ID}")
    print(f"[submit] output={out_path}")

    records = []
    ok = 0
    for i in range(args.count):
        rec = submit_one(i + 1)
        records.append(rec)
        if rec["job_id"]:
            ok += 1
            print(f"  [{i+1:3}/{args.count}] {rec['job_id']}  ({rec['latency_ms']}ms)")
        else:
            print(f"  [{i+1:3}/{args.count}] FAIL status={rec['http_status']} "
                  f"err={rec['error']}")
        time.sleep(args.pace)

    meta = {
        "scenario": args.scenario,
        "count_requested": args.count,
        "count_succeeded": ok,
        "count_failed": args.count - ok,
        "history_id": HISTORY_ID,
        "dataset_id": INPUT_DATASET_ID,
        "started_at": records[0]["submitted_at"] if records else None,
        "finished_at": records[-1]["submitted_at"] if records else None,
        "records": records,
    }
    out_path.write_text(json.dumps(meta, indent=2))
    print(f"\n[submit] {ok}/{args.count} submitted successfully")
    print(f"[submit] written: {out_path}")
    return 0 if ok == args.count else 1


if __name__ == "__main__":
    sys.exit(main())
