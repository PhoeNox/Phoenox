# Deepening

How to deepen a cluster of shallow modules safely, given its dependencies. Assumes the vocabulary in [LANGUAGE.md](LANGUAGE.md) — **module**, **interface**, **seam**, **adapter**.

## Dependency categories

When assessing a candidate for deepening, classify its dependencies. The category determines how the deepened module is tested across its seam.

### 1. In-process

Pure computation, in-memory state, no I/O. Always deepenable — merge the modules and test through the new interface directly. No adapter needed.

### 2. Local-substitutable

Dependencies that have local test stand-ins (PGLite for Postgres, in-memory filesystem). Deepenable if the stand-in exists. The deepened module is tested with the stand-in running in the test suite. The seam is internal; no port at the module's external interface.

### 3. Remote but owned (Ports & Adapters)

Your own services across a network boundary (microservices, internal APIs). Define a **port** (interface) at the seam. The deep module owns the logic; the transport is injected as an **adapter**. Tests use an in-memory adapter. Production uses an HTTP/gRPC/queue adapter.

Recommendation shape: *"Define a port at the seam, implement an HTTP adapter for production and an in-memory adapter for testing, so the logic sits in one deep module even though it's deployed across a network."*

### 4. True external (Mock)

Third-party services (Stripe, Twilio, etc.) you don't control. The deepened module takes the external dependency as an injected port; tests provide a mock adapter.

## Seam discipline

- **One adapter means a hypothetical seam. Two adapters means a real one.** Don't introduce a port unless at least two adapters are justified (typically production + test). A single-adapter seam is just indirection.
- **Internal seams vs external seams.** A deep module can have internal seams (private to its implementation, used by its own tests) as well as the external seam at its interface. Don't expose internal seams through the interface just because tests use them.

## Internal shape: thin Integration over pure Operations (IOSP)

Depth is a property of the *interface*; IOSP governs the *implementation* behind it. A deep module is rarely one big method — it's a thin **Integration** that composes pure **Operations**:

- **Operations** hold the logic — conditions, transformations, calculations — and call no other project modules. They're the in-process parts (category 1), unit-tested directly with no adapter.
- **The Integration** wires Operations and dependencies together with no considerable logic of its own (trivial routing and guards only). This is where **adapters** plug in for category 2–4 dependencies.

So the dependency categories above describe what the *Integration* talks to across the seam; the Operations stay pure regardless of category. When deepening a mixed Operation/Integration module, the move is to **split, then compose**: extract the logic into Operations, leave a thin Integration, and let the Integration be (or sit inside) the deep module.

A deep module whose implementation is itself a single method mixing logic and composition is still an IOSP violation — depth at the interface does not excuse a tangled implementation.

## Testing strategy: replace, don't layer

- Old unit tests on shallow modules become waste once tests at the deepened module's interface exist — delete them.
- Write new tests at the deepened module's interface. The **interface is the test surface**.
- Tests assert on observable outcomes through the interface, not internal state.
- Tests should survive internal refactors — they describe behaviour, not implementation. If a test has to change when the implementation changes, it's testing past the interface.
- **IOSP splits the tests cleanly.** The Integration gets a small number of wiring tests at the interface (the behavioural surface). The Operations get focused unit tests against their own pure logic — an internal-seam exception to "test only at the interface," justified because Operations are stable and pure, not because you want to peek at internal state. Don't fan out unit tests across the Integration's wiring, and don't drive the Operations' logic only through the Integration's interface.
