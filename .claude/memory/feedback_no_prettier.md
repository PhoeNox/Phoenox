---
name: feedback_no_prettier
description: Do not add Prettier to projects — user dislikes its opinionated formatting; use ESLint only for linting.
metadata:
  type: feedback
---

Do not add Prettier (or Prettier-derived formatters) to projects.

**Why:** User dislikes Prettier's opinionated style and had it removed from the AMTS scaffold (2026-07-02).

**How to apply:** When scaffolding or configuring tooling, skip Prettier, its editor-extension recommendations, and `eslint-config-prettier`; lint with ESLint alone. If a scaffold tool bundles Prettier by default, strip it out. Formatting specifics the user does care about are in [[feedback_code_style]].

Exception: TypeScript 7 (Go port, no JS compiler API) breaks typescript-eslint; the user chose oxlint for slingshot on 2026-11-13. Use oxlint wherever typescript-eslint cannot parse the project's TypeScript.
