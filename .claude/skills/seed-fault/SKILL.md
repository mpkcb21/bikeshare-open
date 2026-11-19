---
name: seed-fault
description: Break src/ on purpose to test whether the tests and the leakage hook catch it, then restore it and log the result. Use when asked to seed, inject, or simulate a fault or bug in the pipeline.
allowed-tools: Read, Edit, Bash(python -m pytest*), Bash(make test*), Bash(git diff*), Bash(git status*)
---

# Working tree before you start

!`git status --short`

# Current test state

!`python -m pytest tests -q 2>&1 | tail -1`

# Seeding a fault: $ARGUMENTS

If the working tree above is not empty or the suite is not green, stop and say so. Do not seed a fault on top of unfinished work.

Work in this order.

1. **Say what you will break and which test should catch it.** One sentence each. Only edit files under `src/`. Never touch `data/raw/`, `tests/`, or `.claude/`.

2. **Make the change with the Edit tool.** Never use Bash, sed, or a script: the PostToolUse hook only watches Edit and Write, so a Bash edit is invisible to it. Show the exact diff with `git diff -- src/`.

3. **Report what the hook did.** If the hook sent a message back after the edit, quote it verbatim. If nothing came back, write "hook did not fire" or "hook silent". Do not guess.

4. **Run `python -m pytest tests -q`.** Quote the failing test name and the assertion line. If the suite is still green, the suite has a gap: say so plainly, do not call the fault caught, and describe the test that would have caught it.

5. **Restore the code with the Edit tool**, then run `make test` and confirm it is green again. Check `git diff -- src/` is empty.

6. **Log it.** Add a section at the end of `docs/SEEDED_FAULTS.md` with: the fault, the exact diff, the failing test or "suite stayed green", the hook result from step 3, and how many tool actions the restore took. Do not commit anything.
