# Public Release And Candidate Site Spec

Date: 2026-05-08

## Objective

Publish `agent-systems-proof` as a public GitHub repository and add it to the public Sam Meyer candidate site as a portfolio proof point for agent harness, durability, traces, and eval gates.

## Files

Proof repo:

- `README.md`
- `LICENSE`
- GitHub remote for `swmeyer1979/agent-systems-proof`

Candidate site:

- Existing portfolio/data files under `/Users/sam/.openclaw/workspace/agents/jobhunter/candidate-site`
- Exact files to be selected after inspecting the site data model

## Acceptance Criteria

- Proof repo has a clean commit and public GitHub URL.
- `gh repo view swmeyer1979/agent-systems-proof` reports `PUBLIC`.
- Proof repo verification still passes: `make demo`, `make resume-proof`, `make eval`, `make test`.
- Candidate site references the repo in the existing portfolio/project surface without exposing local paths or generated runtime artifacts.
- Candidate site build passes.

## Risks

- Publishing generated `.runs`, traces, reports, or private local paths would weaken the signal. Keep generated artifacts gitignored.
- Candidate-site data may feed the Ask AI corpus. Avoid local paths and sensitive internal evidence.
- A public repo without a license is ambiguous. Add MIT unless a different license is explicitly required.

## Verification

```bash
git status --short
gh repo view swmeyer1979/agent-systems-proof --json name,visibility,url
npm run build
```

