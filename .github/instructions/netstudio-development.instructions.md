---
name: NetStudio Development
description: "Use when changing NetStudio-Codex source code, tests, dependencies, or build configuration. Covers project structure, established tooling, and validation commands."
applyTo:
  - "netstudio/**/*.py"
  - "tests/**/*.py"
  - "examples/**/*.py"
  - "backend/**/*.js"
  - "frontend/src/**/*.js"
  - "frontend/src/**/*.jsx"
  - "**/package.json"
  - "pyproject.toml"
  - "Makefile"
---

# NetStudio Development

- Preserve the existing Python 3.11+ core and the npm workspaces in `backend/` and `frontend/`. Follow the conventions of the module being changed; avoid broad rewrites or new dependencies without a concrete need.
- Keep changes focused on the request. When changing behavior, add or update a nearby regression test where the existing test structure supports it.
- Protect workspace boundaries, file operations, and external integrations. Validate inputs, avoid exposing secrets, and make consequential side effects explicit.
- Keep documentation consistent with implemented behavior. Distinguish current behavior from proposals and do not claim tests or commands ran without evidence.

## Validation

- Python tests: `make test` (runs `pytest tests/ -v`; pytest configuration also enables coverage).
- Python unit tests: `make test-unit`.
- Python lint and type checks: `make lint` (Black, isort, flake8, and mypy).
- Python formatting: `make format`; use this only when formatting changes are in scope.
- Frontend production build: `npm --prefix frontend run build`.
- Start both Node workspaces for local development: `npm run dev` from the repository root. This is a long-running development server, not a test.
- Build documentation with `make docs` when documentation changes require it.
- The root npm manifest does not define a test script, and the backend manifest does not define test or lint scripts. Do not report `npm test` or a backend test command as available unless the manifests change.
- Run the narrowest relevant check first. Report checks not run and any environmental blockers.