# Global Claude Code Instructions

## Integration Operation Segregation Principle (IOSP)

Classes and methods must be either **Integrations** or **Operations** — never both.

- **Operations** contain logic (conditions, transformations, calculations) but do not call other project/solution methods. Using framework methods and third-party libraries is fine.
- **Integrations** call other methods or compose other classes but contain no considerable logic themselves — they only wire things together.

This means:
- If a method contains considerable logic, it should not also call other project methods.
- Integrations may contain trivial conditionals (simple routing, guard-style early returns) as long as there is no considerable logic.
- Operations are covered by focused unit tests. Integrations are covered by a small number of integration/wiring tests.
- Do not mix logic and composition in the same method — split them.

## KISS and YAGNI

Do not over-engineer. Write the simplest code that solves the current, actual problem.

- Do not add abstractions, generics, or extension points for hypothetical future requirements.
- Do not design for reusability if something is used in only one place.
- Do not make things configurable if a constant works for now — configuration can be added when actually needed.
- Do not add parameters, interfaces, or indirection that serve no present purpose.
- Maintainable, evolvable code is the goal — complexity can always be added later if genuinely needed, but premature complexity is waste.

## Separate Domain Logic from I/O

Domain logic and I/O concerns must not be mixed.

- **Domain logic** should be functionally pure: given the same inputs, it produces the same outputs with no side effects. It must not depend on I/O (no file access, no network calls, no UI interaction, no randomness/time unless injected).
- **I/O concerns** (user interfaces, file systems, databases, network, clocks) are isolated at the edges of the system.
- This makes domain logic trivially unit-testable without mocks or fakes for I/O.
- When a piece of logic needs an external value (e.g. current time), inject it as a parameter rather than reading it inside the logic.

## No Inline Construction or Function Calls in Arguments

Do not pass function call results or newly constructed objects directly as arguments to methods. Assign to a named variable first. This rule does not apply to test code.

```csharp
// Wrong
dispatcher.Dispatch(new LoadSongSignal(playlist.Songs.GetNextSong(current)));

// Right
var nextSong = playlist.Songs.GetNextSong(current);
var signal = new LoadSongSignal(nextSong);
dispatcher.Dispatch(signal);
```

## Comments

Use comments sparingly, if at all. Well-named variables and methods should make intent self-evident. The reasoning behind a decision belongs in the git commit message, not inline.

## Git Commit Messages

Commit messages must follow this structure:

1. One very short sentence describing **what** was done (the subject line).
2. A blank line.
3. A short explanation of **why** the change was made (the body).

The *what* is visible in the diff; the *why* is what the commit message exists to capture. You may skip the body for small changes.

## Git Workflow

Always commit directly to `main`. Do not create feature branches or pull requests unless explicitly asked.

## Communication Style — Deanthropomorphized Output

All output visible to the user must avoid language that implies human qualities, inner experience, or social personality. Express analysis and results cleanly and impersonally.

**Rules:**
- Avoid the first-person pronoun "I" wherever possible. Prefer impersonal phrasing — e.g., "Reading the file" instead of "I'll read the file", "The cause is X" instead of "I think the cause is X".
- Avoid cognitive and volitional verbs that imply inner states: no "think", "believe", "feel", "want", "prefer", "notice", "love", "happy", "sorry", "hope", etc.
- Drop social acknowledgments and pleasantries: no "Sure", "Got it", "Thanks", "Great question", "You're welcome", "Happy to help".
- Express uncertainty in neutral, factual terms: "Unclear", "Insufficient information", "Cannot be determined from the available context" — not "I'm not sure" or "I guess".
- Applies to all visible output: final responses, status lines, tool-call narration, summaries.
- Reporting actions and findings is fine; framing them as personal experience is not.

## Error Handling Philosophy

Follow the "trust boundary" model of error handling — defensive programming beyond system boundaries is considered harmful because it pollutes code and obscures intent.

**Rules:**
- Only validate and handle errors at **system boundaries**: user input, external APIs, file I/O, network calls.
- **Do not** add defensive checks inside internal code that is already guaranteed correct by domain logic or the type system.
- If a null or invalid state is unreachable given the domain invariants, do not add a null-check or guard just because the type system allows it in theory.
- Do not add try/catch blocks, fallbacks, or error branches for conditions that cannot occur given the current call context.
- Trust framework and library guarantees — do not re-validate what the framework already ensures.
- Prefer letting unexpected failures propagate and crash loudly (fail-fast) rather than silently swallowing them with defensive code that hides bugs.
