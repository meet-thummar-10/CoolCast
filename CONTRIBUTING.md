# Contributing to CoolCast

## Workflow
1. Pick an issue from the project board and move it to **In progress**.
2. Update main: `git switch main` then `git pull`.
3. Create a branch: `git switch -c feature/<issue#>-short-name`.
4. Commit small and often: `git commit -m "feat(area): what you did (#issue)"`.
5. Push and open a pull request. Write `Closes #<issue>` in the description.
6. Fix review comments, push again, and reply to each thread.
7. After the leader squash-merges, switch to main and pull.

## Rules
- Never push directly to `main`.
- One issue, one branch, one PR. Keep PRs under about 400 changed lines.
- Run `git status` before every commit. No secrets and no large data files.
- Pull `main` into your branch every day.

## Commit message types
`feat` new feature, `fix` bug fix, `docs` documentation,
`test` tests, `refactor` code change without new behaviour.

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
