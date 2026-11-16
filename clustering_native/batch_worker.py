"""Private persistent JSONL worker for approved stability fits.

One worker per candidate diagnostic batch, never shared between research
sessions or authorization scopes. Request/result payloads stay on disk so pipe
messages are small; a parent may kill the worker on every timeout.
"""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path
import pandas as pd
from .core import write_json
from .engine import fit_one


def serve():
    # Emitted after scientific imports, before any fit request; startup is
    # included in the first fit's existing approved wall-clock budget.
    sys.stdout.write(json.dumps({"status": "READY"}) + "\n")
    sys.stdout.flush()
    for line in sys.stdin:
        try:
            job = json.loads(line)
            if job.get("command") == "close":
                return 0
            if set(job) != {"command", "input", "output", "job_id"} or job["command"] != "fit":
                raise ValueError("Invalid private fit-worker protocol")
            start = time.monotonic()
            args = json.loads(Path(job["input"]).read_text(encoding="utf-8"))
            data = pd.DataFrame(args.pop("data"))
            result = fit_one(data, **args)
            computed = time.monotonic()
            write_json(job["output"], result)
            done = time.monotonic()
            response = {"job_id": job["job_id"], "ok": True,
                        "compute_seconds": computed - start,
                        "write_seconds": done - computed}
        except Exception as exc:
            response = {"job_id": job.get("job_id") if isinstance(job, dict) else None,
                        "ok": False, "error": f"{type(exc).__name__}: {exc}"}
        sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(serve())
