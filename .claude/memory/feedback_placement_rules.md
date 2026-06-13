---
name: feedback_placement_rules
description: Where instructions and memories belong — CLAUDE.md only for universal always-on rules; code/engineering standards go in memory for contextual recall; user/style preferences global, project context project-scoped
metadata:
  type: feedback
---

Two placement decisions.

## CLAUDE.md vs memory

`~/.claude/CLAUDE.md` is loaded into every session regardless of task, so it stays small and holds only instructions that apply universally — currently the deanthropomorphized communication style. Code and engineering standards (architecture, testing, error handling, formatting, commit style) live in memory files instead, so they surface contextually only when a coding task makes them relevant. See [[feedback_code_engineering_principles]] and [[feedback_code_style]].

**Why:** CLAUDE.md is always-on context; carrying code rules in every non-coding session is waste. Memory recall is description-matched, so domain rules appear when working in that domain. (This reverses an earlier policy of putting every stable rule in CLAUDE.md — the always-loaded context cost outweighed the always-on guarantee, and the standards are still enforced via memory recall plus a pointer in CLAUDE.md.)

**How to apply:** A new rule about how to communicate or behave in *every* session → CLAUDE.md. A new code/engineering standard → a feedback memory; add a pointer line under CLAUDE.md's "Code & Engineering Standards" section if it is a major new ruleset. If unsure, ask.

## Global vs project memory

User preferences and coding style apply across projects → save to global memory (`~/.claude/memory/`). Project-specific goals, decisions, constraints, and references → project memory.

**Why:** The user corrected a code-style memory once saved to project scope; cross-project preferences must be global from the start.

**How to apply:** Before saving, ask "would this apply in any project, or only this one?" General (user preferences, coding style, working style) → global. Tied to this specific codebase (goals, decisions, constraints, external references) → project.
