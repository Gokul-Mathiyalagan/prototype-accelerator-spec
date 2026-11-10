---
name: end-session
description: Use when ending a work session on the Prototype Accelerator repo, when asked to hand off, switch tools, wrap up, pause or save progress, after finishing a task, or when context or usage is running low.
---

# End a session (handoff)

The next session may run in a different agent with no memory of this one. Leave the repo so that agent can carry on from `handoff/HANDOFF.md` alone.

Start the handoff while you still have room to finish it. If context or usage is running low, stop feature work and hand off now.

## Steps

1. **Commit all work.** Run `git add -A`, then commit `T-###: wip <what>` with the trailer `Agent: <your agent name>`. Unfinished code is fine on a task branch. Never leave uncommitted changes. If something is half-edited and broken, say so in HANDOFF.md rather than reverting useful work.

2. **Update the task** in `tasks/tasks.yaml`:
   - `status`: `in_progress` if work remains, `review` if every acceptance criterion is met and `make check` passes, or `blocked` with the reason.
   - `progress`: one line, for example "Parser and models done; CLI command and tests remain."
   - Leave `owner` as your agent name. The next agent changes it when it takes over.

3. **Rewrite `handoff/HANDOFF.md`** from `handoff/TEMPLATE.md`. Rules:
   - Name exact files, functions, tests and commands.
   - The "Next step" must be something an agent can do immediately, for example "Implement `parse_manifest()` in `packages/accel-extract/src/accel_extract/inventory/manifests.py` so that `tests/extract/test_manifests.py::test_pyproject` passes."
   - List every acceptance criterion as done or not done.
   - Record decisions you made that aren't in the spec, and any assumptions.
   - Keep it under about 80 lines. Detail goes in the log.

4. **Write the session log** at `handoff/log/<YYYY-MM-DD>-<agent>-T-###.md`. Include:
   - what you did, in order;
   - commands you ran that matter, and their results;
   - **tried and didn't work**, and why (this saves the next agent the most time);
   - links to relevant files.

5. **Validate.** Run `make handoff-check` and fix anything it reports. If you edited anything in `.agents/skills/`, also run `make sync-agent-files`.

6. **Commit the handoff:** `T-###: handoff`, with the trailer `Agent: <your agent name>`.

7. **Tell Gokul** in one or two sentences: the branch, the task status, and the next step.

## When a task moves to review

Also check that:
- every acceptance criterion in `tasks.yaml` is met, and you can say how you verified each one;
- tests cover the new behavior;
- any spec change has an ADR or a note in HANDOFF.md;
- HANDOFF.md says what Gokul should review, and names the next task to start.
