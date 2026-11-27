"""Write data/status.json: when each bank's live page was last checked, and
what the check found. The site uses it to tell "the bank hasn't published a
newer rate" apart from "our scraper couldn't read the bank's page".

Shape:
    {
      "checkedAt": "2026-11-27T16:05:12+05:30",      # newest check in the file
      "banks": {
        "State Bank of India": {
          "checkedAt": "...",
          "result": "ok" | "waiting" | "error",
          "rateDate": "2026-11-27",                    # date on the bank's page (ok/waiting)
          "error": "...",                              # short reason (error only)
          "lastOkAt": "...",                           # last check that read the page
          "failingSince": "..."                        # first check of the current error run
        }
      }
    }

Banks not checked in this run (a retired bank, or a BANKS subset run
locally) keep their previous entry.
"""
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

DATA_DIR = os.environ.get("TTBUY_DATA_DIR", "data")
STATUS_PATH = os.path.join(DATA_DIR, "status.json")
MAX_ERROR_LEN = 200


def now_ist():
    return datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(timespec="seconds")


def merge_status(previous, checks):
    """Return a new status dict: previous entries updated with this run's checks."""
    banks = dict(previous.get("banks", {}))
    for name, check in checks.items():
        prev = banks.get(name, {})
        entry = {"checkedAt": check["checkedAt"], "result": check["result"]}
        if check["result"] == "error":
            entry["error"] = (check.get("error") or "Unknown error")[:MAX_ERROR_LEN]
            still_failing = prev.get("result") == "error" and prev.get("failingSince")
            entry["failingSince"] = prev["failingSince"] if still_failing else check["checkedAt"]
            if prev.get("lastOkAt"):
                entry["lastOkAt"] = prev["lastOkAt"]
        else:
            entry["rateDate"] = check.get("rateDate")
            entry["lastOkAt"] = check["checkedAt"]
        banks[name] = entry

    checked = [b["checkedAt"] for b in banks.values() if b.get("checkedAt")]
    return {"checkedAt": max(checked) if checked else None, "banks": dict(sorted(banks.items()))}


def write_status(checks, path=STATUS_PATH):
    previous = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            previous = json.load(f)
    status = merge_status(previous, checks)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Saved {path} ({len(checks)} checks)")
