# Maintaining the profile

Run on Linux with Python 3, Git, Bun 1.4.4, and Rust/Cargo 1.99.1:

```sh
python3 -m unittest discover -s scripts -v
python3 scripts/check.py
```

No Python packages, credentials, services, or API keys are required. Git and
package registries need network access. Each run clones public repositories
into temporary directories. Quanta's source and license are left untouched.
Review and change the full commit IDs in `scripts/check.py` deliberately.
These checks establish health of those revisions, not each project's latest branch.

`README.template.md` owns the prose; `README.md` is generated. `banner.ps` owns
the art; `assets/banner.svg` is stdout from psi's `Interpreter.eval`, through a
small generated TypeScript adapter using the same API as psi's REPL. The art
is a family of cubic curves, not cellular automata. SVG is validated before
replacement. On render failure, the last valid banner stays and the check fails.

The runner records the exact command, UTC start, duration, revision, exit code,
and combined output in `results/latest.json`. README output previews are capped
at the last 12 lines / 1,600 characters per command; JSON retains complete output. Exit 124
means timeout, 125 means the attempt did not finish, 127 means a missing command.
Any nonzero step makes the project visibly FAIL. A pending result replaces the
previous status before work begins, and results are saved after each project.

The nightly workflow uses GitHub-hosted Linux, immutable action revisions,
frozen/locked project dependencies, and explicitly selected toolchain versions.
The runner image, network, and registries are not hermetic. Checks execute with
read-only repository permission and no persisted checkout credentials. Only
the publishing job has contents write permission; it executes no project code.
It downloads generated files and commits the allowlisted outputs, including
failures. If the artifact is unavailable it commits a fresh incomplete/FAIL
result. The job remains red when a check fails. Push-trigger path filters avoid
a generated-output loop. Pull requests run checks without publishing.

Actions schedules can be delayed or disabled; cancellation, runner loss, a
repository write restriction, or a failed publishing job can prevent a status
update. Always read the attempt timestamp. The profile does not claim live health.
No workflow was activated or remotely executed during implementation.

Quanta checks run `cargo test --locked -p quanta-core-rs`, not its full workspace,
Elixir suites, browser demos, networking, or load tests. No scale claim follows
from this check. The reviewed setup has a separate `make particle-wasm` step.
No source, setup, or license changes to Quanta are included.

The six README project cards also serve as the proposed pin selection. Actual
GitHub pins and repository descriptions require separate account changes and
are outside this implementation.

Implementation references: [GitHub workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax),
[Bun install](https://bun.sh/docs/pm/cli/install), [Bun tests](https://bun.sh/docs/test),
[Cargo test](https://doc.rust-lang.org/cargo/commands/cargo-test.html),
[Python subprocess](https://docs.python.org/3/library/subprocess.html).
