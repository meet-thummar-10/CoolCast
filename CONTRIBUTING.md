# Contributing to CoolCast

## Workflow
1. Pick your issue on the project board and move it to **In progress**.
2. Update main: `git switch main` then `git pull`.
3. Create the branch named in the issue: `git switch -c feature/<issue#>-short-name`.
4. Add your changes, then run `ruff check .` and `pytest`. Both must pass.
5. Commit: `git commit -m "feat(area): what you did (#issue)"`.
6. Push: `git push -u origin feature/<issue#>-short-name`.
7. Open a pull request. Fill in the template and write `Closes #<issue>`.
8. Fix review comments, push again, and reply to each thread.
9. After the leader squash-merges, switch to main and pull.

## Rules
- Never push directly to `main`.
- One issue, one branch, one PR. Keep PRs under about 400 changed lines.
- Run `git status` before every commit. No secrets and no large data files.
- Pull `main` into your branch every day.

## Commit message types
`feat` new feature, `fix` bug fix, `docs` documentation,
`test` tests, `refactor` code change without new behaviour,
`chore` setup and tooling.

## Review checklist
- [ ] Solves the linked issue and nothing extra
- [ ] Formulas match the spec (ratio of sums, units, kW to kWh)
- [ ] Tests added or updated, and CI is green
- [ ] No hard-coded paths, secrets or large files
- [ ] Assumptions are labelled in the UI (measured, modelled, assumed)
- [ ] Code is readable, with docstrings on public functions
- [ ] The app still runs from a clean checkout

## Definition of done
Works with the demo data, tests pass, reviewed, merged to main.
