"""Regenerate ARCHITECTURE.md's reachability column from `make audit`.

**Why this exists.** That column used to be hand-maintained and mixed two
different axes: *role* (LIB, ENTRY, RESEARCH) and *reachability* (LIVE, ORPHAN).
Rows compared on the wrong axis disagree with reality by construction, and eight
of them did. Worse, the reachability half was decided by reading imports, which
misses make targets entirely -- `preseason_report.py` and `demo_pipeline.py` were
both filed ORPHAN while having make targets.

So the column is now **purely reachability, and generated**. Role is not
duplicated here at all; the Notes column already conveys it in prose, where it
cannot silently contradict a fact. Run `make sync-arch` after any wiring change.

Idempotent: running it on an already-synced file changes nothing.
"""

from __future__ import annotations

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from audit_integration import classify

REPO = pathlib.Path(__file__).resolve().parent.parent
ARCH = REPO / "ARCHITECTURE.md"

SHORT = {
    "LIVE (launchd service)": "LIVE",
    "MANUAL (make target)": "MANUAL",
    "RESEARCH (notebook)": "RESEARCH",
    "PARKED (decided, no action)": "PARKED",
    "TESTED ONLY (undecided -- wire or park)": "UNDECIDED",
    "UNREFERENCED": "UNREF",
}

HEADER_OLD = "| Module | Imported by | Status | Notes |"
HEADER_NEW = "| Module | Imported by | Reach | Notes |"
# The status group must accept the multi-value form this script itself emits
# (`**LIVE / MANUAL**`, for a row naming two modules whose reach differs).
# With `\w+` such a row failed to match, was copied through untouched, and was
# never re-synced again -- precisely the silent drift this script exists to
# prevent. Latent until two co-listed modules diverge.
ROW = re.compile(r"^\|\s*(`[^|]+`)\s*\|([^|]*)\|\s*\*\*([\w /]+)\*\*\s*\|(.*)\|\s*$")


def _reach_by_basename() -> dict[str, str]:
    out: dict[str, list[str]] = {}
    for cat, mod in classify():
        out.setdefault(mod.rsplit(".", 1)[-1] + ".py", []).append(SHORT.get(cat, cat))
    # only unambiguous basenames are trusted; a collision is left alone
    return {k: v[0] for k, v in out.items() if len(v) == 1}


def sync(text: str) -> tuple[str, int]:
    reach = _reach_by_basename()
    out, changed = [], 0
    for line in text.splitlines():
        if line.strip() == HEADER_OLD:
            out.append(HEADER_NEW)
            continue
        m = ROW.match(line)
        if not m:
            out.append(line)
            continue
        modcell, imported, status, notes = m.groups()
        names = re.findall(r"`([\w/]+\.py)`", modcell)
        vals = [reach.get(n.rsplit("/", 1)[-1]) for n in names]
        if not names or any(v is None for v in vals):
            out.append(line)
            continue
        new_status = " / ".join(dict.fromkeys(vals))
        if new_status != status:
            changed += 1
        out.append(f"| {modcell} |{imported}| **{new_status}** |{notes}|")
    return "\n".join(out) + ("\n" if text.endswith("\n") else ""), changed


def main() -> None:
    text = ARCH.read_text()
    synced, changed = sync(text)
    ARCH.write_text(synced)
    print(f"ARCHITECTURE.md: {changed} reachability cell(s) updated")


if __name__ == "__main__":
    main()
