---
name: Global vs Project Memory Classification
description: User preferences and coding style that apply across projects must go in global memory, not project memory
type: feedback
---

When saving a memory about the user's general preferences or coding style, save it to global memory (`~/.claude/memory/`), not to a project-specific directory.

**Why:** The user corrected me when I saved code style preferences to the project memory — they should have been global from the start.

**How to apply:** Before saving a memory, ask: "Would this apply in any project, or only this one?" If it applies generally (user preferences, coding style, working style), save globally. Only use project memory for things tied to this specific codebase: project goals, decisions, constraints, external references for this project.