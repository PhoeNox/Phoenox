---
name: CLAUDE.md vs Memory — where explicit rules belong
description: When the user states an explicit, stable coding rule or preference, put it in CLAUDE.md rather than saving a memory
type: feedback
---

When the user explicitly states a stable, universal rule or coding standard, add it to the appropriate `CLAUDE.md` (global `~/.claude/CLAUDE.md` or project-level) rather than saving it as a memory.

**Why:** CLAUDE.md is the user's curated, always-loaded instruction file — it's the right home for explicit, durable standards the user wants enforced every time (e.g. IOSP, KISS/YAGNI, commit message structure). Memory is better suited to softer, context-dependent learnings: things picked up implicitly, past incidents, preferences about tone, or observations about the user's working style. Putting an explicit rule into memory buries it behind a lookup and fragments standards across two places.

**How to apply:** When the user says something like "my global preference is X" or "commit messages should always Y" — default to editing CLAUDE.md (global for cross-project rules, project-level for project-specific ones). Reserve memory for: corrections tied to a specific incident, confirmations of non-obvious approaches, facts about the user's role or expertise, project context, and external-system references. If unsure which fits, ask.