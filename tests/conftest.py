from pathlib import Path

import pytest

STATIC_DIR = Path("data/static")


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "static_data(*files): needs these nflverse files in data/static/ (built by `make data`)",
    )


def pytest_runtest_setup(item):
    # data/static/ is not tracked in git, so on a fresh clone these real-data
    # checks have nothing to read. Skip with the fix rather than fail on a
    # missing file, which would look like a code bug.
    for marker in item.iter_markers(name="static_data"):
        missing = [f for f in marker.args if not (STATIC_DIR / f).exists()]
        if missing:
            pytest.skip(f"run `make data` first; missing {', '.join(missing)}")
