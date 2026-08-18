.PHONY: venv install test lint demo collect collect-once preseason-poll preseason-report props-poll \
	collector-service-install collector-service-uninstall collector-service-status \
	monitor-scan-once monitor-service-install monitor-service-uninstall monitor-service-status \
	props-collect props-collect-once \
	props-service-install props-service-uninstall props-service-status clean

VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

venv:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip

install: venv
	$(PIP) install -e ".[dev]"

test:
	$(PY) -m pytest -q

lint:
	$(PY) -m ruff check src tests

# Walks the whole live pipeline (pull -> store -> compare -> decide ->
# notify) on made-up odds -- no API call, no credits spent, sends a real
# (clearly-labeled DEMO) text if ALERT_PHONE_NUMBER is set in .env. See
# src/demo_pipeline.py for what to tweak.
demo:
	$(PY) -m src.demo_pipeline

collect:
	$(PY) -m src.collect.run

collect-once:
	$(PY) -m src.collect.run --once

# Preseason dry run (src/collect/preseason.py): invoke by hand a handful of
# times during the preseason window, not on a schedule -- see that module's
# docstring for why (shared Odds API credit budget with the real season).
preseason-poll:
	$(PY) -m src.collect.preseason

preseason-report:
	$(PY) -m src.clv.preseason_report

# Player props (src/collect/props.py): PREPPED, NOT ACTIVE as of 2026-08-17
# -- live-checked and confirmed NFL props aren't posted this far before
# kickoff (only DraftKings, one market, no Pinnacle). Don't run this on a
# schedule; it's here so it's ready once props actually start filling in.
# Defaults to games in the next 7 days; pass a different day count as an
# arg, e.g. `make props-poll ARGS=3`.
props-poll:
	$(PY) -m src.collect.props $(ARGS)

# Automated, budget-aware live props polling (src/collect/props_scheduler.py) --
# unlike props-poll above (manual, polls everything in the window at once),
# this schedules two real polls per event (entry near when props post, close
# near kickoff) and persists per-event state so it never re-polls a finished
# event. Uses ODDS_API_KEY_PAID, NOT ODDS_API_KEY -- a separate credit pool
# from the mainline collector's free tier, deliberately, so props polling
# can never starve the collector's own dense pre-kickoff CLV polling. See
# src/collect/props_budget.py's module docstring for the full reasoning.
props-collect:
	$(PY) -m src.collect.props_run

props-collect-once:
	$(PY) -m src.collect.props_run --once

# Real-season collector as a persistent background service (macOS launchd),
# so it survives terminal closes, sleep, and reboots -- `make collect` alone
# blocks in the foreground and dies with the terminal. Source of truth for
# the plist is ops/com.nflclv.collector.plist (checked into git); these
# targets just install/remove the copy launchd actually reads from.
COLLECTOR_AGENT := $(HOME)/Library/LaunchAgents/com.nflclv.collector.plist

collector-service-install:
	mkdir -p logs
	cp ops/com.nflclv.collector.plist $(COLLECTOR_AGENT)
	launchctl bootstrap gui/$$(id -u) $(COLLECTOR_AGENT)
	@echo "installed and started -- check with 'make collector-service-status'"

collector-service-uninstall:
	launchctl bootout gui/$$(id -u)/com.nflclv.collector || true
	rm -f $(COLLECTOR_AGENT)

collector-service-status:
	launchctl list | grep com.nflclv.collector || echo "not running"
	@echo "--- last 20 log lines ---"
	tail -n 20 logs/collector.log 2>/dev/null || echo "(no log yet)"

# Live +EV monitor (src/notify/): scans the real-season store for
# execution-book prices that beat Pinnacle's fair value and texts about
# them. Reads local files only -- no Odds API cost, runs independently of
# and more often than the collector. Needs ALERT_PHONE_NUMBER in .env to
# actually send anything; without it, it scans and logs in dry-run mode.
monitor-scan-once:
	$(PY) -m src.notify.monitor_run

MONITOR_AGENT := $(HOME)/Library/LaunchAgents/com.nflclv.monitor.plist

monitor-service-install:
	mkdir -p logs
	cp ops/com.nflclv.monitor.plist $(MONITOR_AGENT)
	launchctl bootstrap gui/$$(id -u) $(MONITOR_AGENT)
	@echo "installed and started -- check with 'make monitor-service-status'"

monitor-service-uninstall:
	launchctl bootout gui/$$(id -u)/com.nflclv.monitor || true
	rm -f $(MONITOR_AGENT)

monitor-service-status:
	launchctl list | grep com.nflclv.monitor || echo "not running"
	@echo "--- last 20 log lines ---"
	tail -n 20 logs/monitor.log 2>/dev/null || echo "(no log yet)"

PROPS_AGENT := $(HOME)/Library/LaunchAgents/com.nflclv.props.plist

props-service-install:
	mkdir -p logs
	cp ops/com.nflclv.props.plist $(PROPS_AGENT)
	launchctl bootstrap gui/$$(id -u) $(PROPS_AGENT)
	@echo "installed and started -- check with 'make props-service-status'"

props-service-uninstall:
	launchctl bootout gui/$$(id -u)/com.nflclv.props || true
	rm -f $(PROPS_AGENT)

props-service-status:
	launchctl list | grep com.nflclv.props || echo "not running"
	@echo "--- last 20 log lines ---"
	tail -n 20 logs/props.log 2>/dev/null || echo "(no log yet)"

clean:
	rm -rf $(VENV) .pytest_cache **/__pycache__
