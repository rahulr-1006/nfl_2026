"""Which src/ modules are actually reachable, and from what?

**Why this exists.** Modules in this repo get built, validated, and then quietly
stop being wired to anything -- and the drift is invisible until someone trips
over it. Rediscovering it by hand each time is how stale code, stale constants
and stale docs survive. This makes the question one command.

Reachability is computed from the *real* entrypoints, of which there are three
kinds, and missing any one of them produces a falsely alarming answer:

  1. **launchd services** (`ops/*.plist`) -- the things actually running 24/7.
  2. **Make targets** (`python -m ...` in the Makefile) -- hand-invoked, often
     deliberately so. `middle_scan`/`steam_scan` are manual *on purpose*: they
     have no live track record yet and are not trusted to an unattended alert
     channel. Manual is a decision here, not neglect.
  3. **Notebooks** -- research code. `src/model/*` is mostly this, and calling
     it "orphaned" because no service imports it would be wrong.

Anything left over is either **PARKED** (a module whose docstring records an
explicit park verdict -- a decision, so it should not keep resurfacing as an open
question), test-only (built and validated but wired to nothing, and *undecided*),
or completely unreferenced. Only the undecided ones need attention.

Run: `make audit`
"""

from __future__ import annotations

import ast
import json
import pathlib
import re
from collections import Counter, deque

REPO = pathlib.Path(__file__).resolve().parent.parent
IMPORT_RE = re.compile(r"from (src[\w.]*) import|import (src[\w.]+)")


def _src_imports(text: str) -> set[str]:
    return {a or b for a, b in IMPORT_RE.findall(text)}


def _module_graph() -> tuple[dict[str, pathlib.Path], dict[str, set[str]]]:
    mods, edges = {}, {}
    for f in (REPO / "src").rglob("*.py"):
        if "__pycache__" in str(f):
            continue
        name = str(f.relative_to(REPO).with_suffix("")).replace("/", ".")
        mods[name] = f
        edges[name] = _src_imports(f.read_text())
    return mods, edges


def _reach(entries, edges) -> set[str]:
    seen, q = set(), deque(entries)
    while q:
        m = q.popleft()
        if m in seen or m not in edges:
            continue
        seen.add(m)
        q.extend(edges[m])
    return seen


def _service_entrypoints() -> list[str]:
    out = []
    for plist in (REPO / "ops").glob("*.plist"):
        out += re.findall(r"<string>(src\.[\w.]+)</string>", plist.read_text())
    return out


def _make_entrypoints() -> list[str]:
    mk = REPO / "Makefile"
    return re.findall(r"-m (src\.[\w.]+)", mk.read_text()) if mk.exists() else []


def _notebook_entrypoints() -> set[str]:
    found = set()
    for nb in (REPO / "notebooks").rglob("*.ipynb"):
        for cell in json.loads(nb.read_text()).get("cells", []):
            if cell.get("cell_type") == "code":
                found |= _src_imports("".join(cell.get("source", [])))
    return found


def classify() -> list[tuple[str, str]]:
    mods, edges = _module_graph()
    service = _reach(_service_entrypoints(), edges)
    manual = _reach(_make_entrypoints(), edges)
    notebook = _reach(sorted(_notebook_entrypoints()), edges)

    parked = set()
    for m, f in mods.items():
        doc = ast.get_docstring(ast.parse(f.read_text()), clean=False) or ""
        if "PARKED" in doc:
            parked.add(m)

    tested = set()
    for f in (REPO / "tests").rglob("*.py"):
        tested |= _src_imports(f.read_text())

    rows = []
    for m in sorted(mods):
        if m.endswith("__init__"):
            continue
        if m in service:
            cat = "LIVE (launchd service)"
        elif m in manual:
            cat = "MANUAL (make target)"
        elif m in notebook:
            cat = "RESEARCH (notebook)"
        elif m in parked:
            cat = "PARKED (decided, no action)"
        elif m in tested:
            cat = "TESTED ONLY (undecided -- wire or park)"
        else:
            cat = "UNREFERENCED"
        rows.append((cat, m))
    return rows


ORDER = [
    "LIVE (launchd service)",
    "MANUAL (make target)",
    "RESEARCH (notebook)",
    "PARKED (decided, no action)",
    "TESTED ONLY (undecided -- wire or park)",
    "UNREFERENCED",
]


def main() -> None:
    rows = classify()
    counts = Counter(c for c, _ in rows)
    for cat in ORDER:
        print(f"\n{cat}  ({counts.get(cat, 0)})")
        for c, m in rows:
            if c == cat:
                print(f"    {m}")
    print(f"\nTOTAL: {len(rows)} modules")


if __name__ == "__main__":
    main()
