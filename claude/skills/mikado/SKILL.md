---
name: mikado
description: Apply the Mikado Method to non-trivial changes in existing code. Use for bugfixes, features, or refactorings that are more than a handful of lines, likely touch multiple files, or where a naive attempt might plausibly break something. Skip for obvious one-line fixes, brand-new files, or changes where the outcome is clearly safe.
---

# Mikado Method Skill

You are applying the Mikado Method to a change in existing code. The core invariant is: **the codebase is always in a working state between steps, and failed experiments are always reverted.**

## When to use this skill

Judgement-based trigger. Activate when:
- The change is likely to touch multiple files
- A naive attempt might plausibly break something
- Scope is larger than a handful of lines
- You can't confidently predict what will break

Skip when:
- The fix is obvious and contained (one-line bugfix, typo)
- Working in brand-new files where nothing exists to break
- The user explicitly asks to bypass the method

If you are unsure whether a task qualifies as non-trivial, ask the user before starting.

## The loop

### 1. Confirm the goal

Restate the goal in your own words. Ask the user to confirm before touching any code. Do **not** start experimenting until the goal is confirmed.

### 2. Check preconditions

- The working tree must be clean. If it isn't, stop and ask the user what to do (commit first? let them stash?). Do not proceed with a dirty tree.
- Create `.mikado.md` at the repo root if it doesn't exist.
- Ensure `.mikado.md` is listed in `.gitignore`. Append it if missing.

### 3. Run the Mikado loop

Repeat until the goal is complete:

**a. Experiment.** Delegate to the `hacker` agent with the current goal or sub-goal as its brief. The hacker probes the code, discovers what breaks, and returns a report — leaving all changes in the working tree.

**b. Evaluate the result.** The hacker's report will say one of two things:

- **"Prerequisites found"** — the goal is not yet a leaf. You must stash the hacker's work before switching to a prerequisite: run `git stash push -u -m "mikado-experiment: <brief>"` (the `-u` flag captures untracked files). Verify with `git status` that the tree is clean. The stash stays in place as reference material; do not drop it.
- **"Ready leaf — no prerequisites found"** — the hacker's attempt is a valid starting point. Leave the changes in the working tree so the clean-code-developer can build on them. **Do not stash.**

**c. Update the graph.** Write any discovered prerequisites into `.mikado.md` as children of the current node.

**d. Present to the user.** Show the updated graph. List the available leaves (nodes with no unchecked children). Ask the user which one to tackle next. **Always ask — never auto-pick**, even if there's only one obvious choice, unless the user has explicitly told you otherwise in this session.

**e. Implement the leaf.** Delegate to the `clean-code-developer` agent with the chosen leaf as a single, well-scoped brief. If the hacker left changes in the tree for this leaf, mention that in the brief so the developer knows there is a starting point. It must produce: compiling code, tests (if applicable), a self-review pass, and one commit. It returns success (with SHA) or failure.

**f. Handle the result.**
- On success: confirm the repo is still green, mark the leaf as done in `.mikado.md` with its short SHA, then ask the user on which prerequisite the hacker should work next and loop.
- On failure because the leaf had hidden prerequisites: do not retry blindly. Stash the current state with `git stash push -u -m "mikado-experiment: <brief>"`, update the graph with the hidden prerequisites, then ask the user on which prerequisite the hacker should work next and loop.
- On any other failure: stop and ask the user how to proceed.

**g. Repeat** until the original goal itself has become a safe leaf. Then implement it (step e) and you're done.

### 4. Cleanup

When the goal is fully implemented:
- Delete `.mikado.md`.
- Run `git stash list` and drop **every** stash entry whose message starts with `mikado-experiment:`. Use `git stash drop stash@{N}` for each, working from the highest index down so earlier indices don't shift. Do not touch any stash entry you didn't create.
- Verify `git stash list` contains no `mikado-experiment:` entries after cleanup.
- Report what was accomplished and the list of commits created.

If the user abandons a goal partway through, ask before cleaning up the stash entries — they may want to keep the reference material or inspect individual experiments first.

## Graph format (`.mikado.md`)

Plain markdown with nested checkboxes so the user can read and edit it directly:

```markdown
# Mikado Graph

**Goal:** <one-line description>

- [ ] <goal>
  - [ ] <prerequisite A>
    - [x] <leaf A1> — abc1234
    - [ ] <leaf A2>
  - [ ] <prerequisite B>
```

A **leaf** is any unchecked node with no unchecked children. When a leaf is committed, write its short SHA next to it and change `[ ]` to `[x]`.

## Check-in rules

The user wants to stay closely in the loop. Ask first whenever:
- The goal hasn't been confirmed yet
- There are multiple viable leaves (always ask which to pick)
- An experiment reveals scope the user didn't anticipate
- A leaf implementation fails and there are multiple possible recovery paths
- The working tree isn't clean at start
- You're unsure whether the work qualifies as non-trivial enough to apply the method

When in doubt, ask.

## Stash hygiene

When you stash a hacker experiment, use the name `mikado-experiment: <brief>`. These accumulate throughout the session as reference material — do not drop them mid-loop. They are cleaned up only during step 4 (final cleanup), and only the ones you can identify as `mikado-experiment:` entries. Never drop stash entries you didn't create.

Stashing only happens in two situations:
1. After a hacker run that **found prerequisites** — you stash before switching to a prerequisite.
2. After a leaf implementation **failed with hidden prerequisites** — you stash the failed attempt before investigating further.

When the hacker concludes that a goal is a **ready leaf**, do **not** stash — leave the work in place for the clean-code-developer.

## Delegating well

When calling `hacker` or `clean-code-developer`, brief them like a colleague who hasn't seen this conversation:
- State the specific goal or leaf in one or two sentences.
- Give the relevant file paths you already know about.
- Say what "done" looks like for their step.
- Do not paste the entire graph — they only need their current task.