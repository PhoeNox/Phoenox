---
name: feedback_code_style
description: Formatting and naming conventions the user applies to C# code — no underscore prefix on private fields; leading boolean operators on continuation lines
metadata:
  type: feedback
---

Code-style specifics. Broader engineering standards are in [[feedback_code_engineering_principles]].

No underscore prefix on private fields — use `search`, not `_search`.

**Why:** User corrected this directly after a code edit.

**How to apply:** When writing or editing C# (including Blazor @code blocks), declare private fields without a leading underscore.

---

In multi-line boolean expressions, place the operator at the **start** of the continuation line, not the end of the previous line.

```csharp
// Correct
s.Artist.Contains(search, StringComparison.OrdinalIgnoreCase)
|| s.Title.Contains(search, StringComparison.OrdinalIgnoreCase)
|| s.Album.Contains(search, StringComparison.OrdinalIgnoreCase)

// Wrong
s.Artist.Contains(search, StringComparison.OrdinalIgnoreCase) ||
s.Title.Contains(search, StringComparison.OrdinalIgnoreCase) ||
s.Album.Contains(search, StringComparison.OrdinalIgnoreCase)
```

**Why:** User finds leading operators easier for humans to read.

**How to apply:** Any time a boolean expression spans multiple lines, break before the operator.