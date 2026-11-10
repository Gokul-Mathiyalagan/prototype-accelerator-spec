UV ?= uv
NEEDS ?=

.PHONY: setup check test test-live schemas golden handoff-check sync-agent-files

setup:
	@$(UV) sync --locked --all-packages
	@$(UV) run --locked --all-packages python scripts/dev.py setup

check test schemas golden handoff-check sync-agent-files:
	@$(UV) run --locked --all-packages python scripts/dev.py $@

test-live:
	@$(UV) run --locked --all-packages python scripts/dev.py test-live --needs "$(NEEDS)"
