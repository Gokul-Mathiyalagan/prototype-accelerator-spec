# Tasks

`tasks.yaml` lists every task needed to build Prototype Accelerator, in phase order. It's the shared to-do list for Claude Code, Codex and Antigravity, and the place where each agent records how far it got.

## Fields

| Field | Meaning |
|---|---|
| `id` | `T-###`. The first digit is the phase (T-1xx is phase 1); phase 0 uses T-001 to T-099. Never reuse an ID. |
| `phase` | 0 to 5 (see `spec/08-roadmap.md`) |
| `title` | Short name, used in branch names |
| `goal` | Why the task exists, in one sentence |
| `spec` | Spec sections to read before starting |
| `depends_on` | Tasks that must be `done` first |
| `needs` | Outside resources for live verification: `azure`, `copilot`, `rea`, `ghidra`, `work-repos` |
| `paths` | Where the work is expected to land (a guide, not a fence) |
| `acceptance` | What must be true to move to `review`. Each item must be checkable. |
| `status` | `todo`, `in_progress`, `blocked`, `review` or `done` |
| `owner` | `null`, `claude-code`, `codex`, `antigravity` or `gokul` |
| `progress` | One line on where the task stands, updated at every handoff |

## Rules

- Only Gokul sets `done`, after review and merge.
- An `in_progress` or `blocked` task must have an `owner`.
- A `blocked` task must say why in `progress`.
- If you find work that isn't covered, add a new task at the end of its phase with the next free ID, `status: todo`, and say so in the handoff. Don't widen the current task.
- If a task turns out to be too big for one or two sessions, split it: give the parts new IDs, make the original depend on them, and record the split in the handoff.
- `python3 scripts/handoff_check.py` validates this file. CI runs it after T-002.
