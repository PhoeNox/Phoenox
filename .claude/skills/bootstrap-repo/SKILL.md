---
name: bootstrap-repo
description: "Layer personal conventions on a repo after /mattpocock-skills:setup-matt-pocock-skills: ticket conventions, a module map, and a check guardrail."
disable-model-invocation: true
---

# Bootstrap repo

An overlay on the plugin's setup. The plugin owns `docs/agents/*.md` and the `## Agent skills` block. This skill adds only what the plugin leaves out. Each section edits files in place and leaves the plugin's text as it is.

## 1. Explore

- `docs/agents/issue-tracker.md` missing → tell the user to run `/mattpocock-skills:setup-matt-pocock-skills` first, then stop.
- Read `docs/agents/issue-tracker.md` (which tracker: local markdown, GitHub, GitLab, other), `docs/agents/triage-labels.md`, and `CLAUDE.md`/`AGENTS.md`.
- Read the build manifest (`package.json` or the language's equivalent), `.githooks/`, `core.hooksPath`, and `.github/workflows/` or `.gitlab-ci.yml`.
- List the source directories, to draft the module map.
- Note each section's prior output. A section already in place gets updated, never duplicated.

## 2. Draft, confirm, write

Show the user a draft of every file change from the sections below in one message. Let them edit it, then write it. Done when every section is written or the user dropped it.

### Ticket conventions

Append to `docs/agents/issue-tracker.md`, under its `## Conventions` list and as its own sections:

- **Touches line**: each ticket names the modules it changes (names from `docs/architecture.md`), so implementation reads those first. Local tracker: a `Touches:` line under `Status:`. GitHub/GitLab: a `Touches:` line at the top of the body.
- **Closing a ticket**: say what closing means for this tracker. Local: `Status: done` plus ticked checkboxes, no commit needed since `.scratch/` is git-ignored. GitHub/GitLab: `gh issue close` / `glab issue close` with the commit hash. The timing (only after the approved commit succeeds) is global steering, so leave it out here.
- **Bugs found along the way**: a bug the user reports that the session does not fix becomes its own ticket with `needs-triage`, holding the user's words and what was ruled out.

Local tracker only: add a `done` row (`—` | `done` | Implemented and committed) to the table in `docs/agents/triage-labels.md`, and add "plus `done`" to the triage labels line of the `## Agent skills` block.

### Module map

Write `docs/architecture.md`: an `# Module map` heading, one line ("Read the modules a change touches; skip the rest. Tests sit next to their module."), then one table per source directory with `| Module | Responsibility |`.

- Each row is one sentence: the module's gist and its seams (pure core vs I/O adapter). The code and the glossary hold the detail; a row that lists behaviours is sprawl.
- Add a section for non-code files that steer behaviour and that no module names, such as markup, stylesheets and config.

Add to `CLAUDE.md`/`AGENTS.md`:

```markdown
## Navigation

Module map: `docs/architecture.md`. Read the modules a ticket's `Touches:` line names instead of dumping the source tree.
```

### Guardrail

One command runs every check, and both the commit and CI run it.

- **Check command**: `check` = typecheck + lint + test in the manifest (npm: `"check": "npm run typecheck && npm run lint && npm test"`). Lint follows `~/.claude/memory/feedback_no_prettier.md`. A repo with stylesheets also gets `stylelint` with `stylelint-config-standard` in `lint`.
- **Pre-commit hook**: `.githooks/pre-commit` (executable) holding `exec npm run --silent check`, plus `"prepare": "git config core.hooksPath .githooks"` so a fresh install wires it.
- **CI**: a job on push to the default branch that installs and runs `check`. If a workflow already exists, add the step to it.
- **Licensing**: a repo with `REUSE.toml` gets every new config file annotated there.

Leave the checks unrun. The first commit runs them through the hook, so tell the user to expect findings in existing code then.

## 3. Report

List every file written or changed, and every section that was skipped and why.
