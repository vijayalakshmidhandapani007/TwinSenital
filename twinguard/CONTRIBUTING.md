# Working agreement

- `main` is protected. Work merges into `develop` through pull requests, then `develop` is merged to `main` at checkpoints.
- One short-lived branch per task, named `feat/<module>-<task>`, for example `feat/twin-confidence`.
- Every pull request gets one review from a teammate.
- Stay in your own folders (see `.github/CODEOWNERS`). Dashboard pages: one file per member.
- `contracts/` changes only by pull request approved by all four members. Announce the change in the group chat first.
- Never commit `.env`, API keys or passwords.
- Daily 10-minute check-in: blockers and contract changes only.
- Scope: non-weapon components, synthetic specifications, simulated events on an isolated test network.
