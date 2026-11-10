---
name: start-session
description: Use at the start of every work session on the Prototype Accelerator repo, and whenever asked to continue, resume, pick up or carry on the work, including work another agent started.
---

# Start a session

Another agent (Claude Code, Codex or Antigravity) may have done the last session. Its chat history is gone; only the repo remains. Rebuild your picture of the work from the repo before you change anything.

## Steps

1. **Read the handoff.** Open `handoff/HANDOFF.md`. Note the active task, the branch, the commit, and the "Next step".
2. **Check git.**
   - `git fetch --all --prune` (skip this if there's no remote)
   - `git status`: the tree should be clean.
   - `git branch --show-current`: this should match the branch in HANDOFF.md.
   - `git log --oneline -10`: the last commit should be the `T-###: handoff` commit, or later.
   If the branch differs, check out the one HANDOFF.md names. If the tree is dirty and HANDOFF.md doesn't explain it, stop and ask Gokul.
3. **Read the task.** Find it in `tasks/tasks.yaml`. Read `goal`, `acceptance`, `depends_on`, `needs`, `paths` and `progress`.
4. **Read the spec.** Read the sections listed in the task's `spec` field, plus any ADR that HANDOFF.md mentions. Don't read the whole spec.
5. **Read the latest log** in `handoff/log/` for this task, especially "Tried and didn't work".
6. **Verify the baseline.** Run `make check`. Before T-001 replaces the Makefile, it runs only the handoff and skill-mirror checks. Compare the result with "How to verify" in HANDOFF.md. If something that was passing now fails, investigate that first.
7. **Confirm with Gokul.** In two or three lines: the task, what's already done, and what you'll do next. Then start.

## If there's no active task

1. In `tasks/tasks.yaml`, pick the first task with `status: todo` whose `depends_on` are all `done` and whose `needs` you can meet here.
2. Create the branch: `git switch -c task/T-###-<short-name> main`.
3. Set `status: in_progress` and `owner: <your agent name>`, then commit `T-###: claim`.
4. Update `handoff/HANDOFF.md` with the newly active task.

## If something doesn't add up

If HANDOFF.md, `tasks.yaml` and git disagree (for example, the task says `review` but the branch has uncommitted work), don't guess. Tell Gokul what you found and ask which state is right.
