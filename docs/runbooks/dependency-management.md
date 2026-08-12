# Dependency management and vulnerability review

This runbook is the canonical CRM-015 workflow for changing and verifying dependency
graphs. Normal builds install committed locks; they never resolve the human-edited
source declarations.

## Python dependency files

- `backend/requirements.in`: direct runtime declarations and allowed ranges.
- `backend/requirements-dev.in`: exact direct quality tools, constrained by the runtime
  lock.
- `backend/requirements.lock`: exact hash-checked runtime graph.
- `backend/requirements-dev.lock`: exact hash-checked quality graph.

The supported resolver is Linux on Python 3.13.15 with pip-tools 7.6.1. Generate both
locks from the repository root without installing a global tool:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env PIP_CACHE_DIR=/tmp/pip-cache \
  --env PYTHONPATH=/tmp/lock-tools \
  --mount type=bind,source="$PWD/backend",target=/workspace \
  --workdir /workspace \
  python:3.13.15-slim@sha256:ffb752e139c0a19692a43af8d8523b274222dd68eebad5d583b45c2201c6e30a \
  sh -ec 'python -m pip install --disable-pip-version-check --target /tmp/lock-tools --require-hashes -r requirements.lock -r requirements-dev.lock >/dev/null && ./scripts/compile-locks.sh'
```

The script does not request blanket upgrades. Existing lock versions remain preferred.
To update one package intentionally, pass pip-compile's explicit upgrade option after
the script name, for example `./scripts/compile-locks.sh --upgrade-package fastapi` in
the same canonical container. Never edit generated locks by hand.

For every dependency or resolver change:

1. edit only the relevant `.in` declaration or pinned toolchain value;
2. generate both locks in the canonical container;
3. review every version, origin, and hash diff, including transitive changes;
4. run the clean install, reproducibility, vulnerability, and repository quality gates;
5. commit source declarations and generated locks together.

Changing Python patch versions, pip-tools, pip, base-image digests, or the resolver
platform is a reviewed toolchain change. It is not an incidental lock refresh. A
pip-tools change is bootstrapped as its own review: use the previously locked compiler
to produce the proposed lock, update the script's expected version in the same diff,
then rerun the command above from the proposed hash-checked lock before accepting it.

## Clean install and byte-for-byte reproduction

CI installs both graphs with pip hash enforcement:

```bash
python -m pip install --disable-pip-version-check --require-hashes \
  -r backend/requirements.lock -r backend/requirements-dev.lock
```

After that locked install, run the same freshness check used by CI:

```bash
cd backend
./scripts/verify-locks.sh
```

The verifier regenerates into a temporary directory and uses byte comparisons. Any
resolver output drift fails; it does not rewrite the working tree.

## Python vulnerability audit

The audit wrapper validates the exception registry, scans both installed lock graphs
without invoking pip's resolver, prints findings, and retains JSON:

```bash
cd backend
python -m quality.audit_dependencies --output artifacts/pip-audit.json
```

The default exception registry is empty. A finding fails CI. Do not add a raw
`--ignore-vuln`, allow-failure step, or shell exit suppression. If a finding is a
verified false positive or has only an upstream fix, add a reviewed entry to
`backend/pip-audit-exceptions.toml` with all fields below:

```toml
[[exceptions]]
advisory_id = "GHSA-xxxx-yyyy-zzzz"
package = "exact-normalized-package-name"
version = "1.2.3"
justification = "Applicability analysis and compensating control."
tracking_url = "https://github.com/AgustinArispe/AsfaltosCRM/issues/123"
owner = "FAA CRM team"
approved_on = 2026-08-12
expires_on = 2026-09-12
```

The advisory ID and exact locked package/version must match. Expired, duplicate,
malformed, or stale-version entries fail before the scanner runs. Reviewers must verify
the advisory, assess reachability, set a short expiry, and keep the tracking issue
current. Remove the exception as soon as a reviewed fixed version is available.

## Frontend dependencies

Frontend dependencies remain reproducible through `frontend/package-lock.json` and
`npm ci`. Change a dependency with an explicit package/version command, review the
manifest and lock diff together, then run Biome, coverage, TypeScript/Vite build, and
`npm audit --audit-level=high`. Do not hand-edit `package-lock.json` or install frontend
quality tools globally.
