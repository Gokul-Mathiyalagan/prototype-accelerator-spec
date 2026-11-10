# Minimal Makefile until T-001 replaces it with the full set of targets.
# Before T-001, `make check` runs only the handoff checks.

PY ?= python3

.PHONY: check handoff-check sync-agent-files

check: handoff-check
	@$(PY) scripts/sync_agent_files.py --check

handoff-check:
	@$(PY) scripts/handoff_check.py

sync-agent-files:
	@$(PY) scripts/sync_agent_files.py
