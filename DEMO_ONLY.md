# PULSE CRM demo only

This branch is exclusively for promotional and demo work. It contains PULSE CRM branding and is reserved for future fake demo data.

- Do not merge `demo/pulse-video` into `main` without explicit review.
- Never use production services, credentials, customer data, messages, or backups from this branch.
- Run the demo with `scripts/pulse-demo.sh` and its isolated local PostgreSQL volume.
- The demo uses the fake WhatsApp provider. No Meta or production web intake integration is configured.

## Local run

Run `./scripts/pulse-demo.sh up -d --build --wait` from this worktree. The helper generates a private, ignored `.env.demo` on first use and starts the frontend at `http://127.0.0.1:15173`, the API at `http://127.0.0.1:18000`, and PostgreSQL at `127.0.0.1:15432`. Run `./scripts/pulse-demo.sh down` to stop it. Its named volumes are separate from the production and canonical local stacks. Create a local supervisor interactively with `./scripts/pulse-demo.sh exec backend python -m app.scripts.create_supervisor --email demo@pulse.test --full-name 'Demo PULSE'` when login access is needed.

## Later demo data

Use synthetic names and contact details only. A later task may seed fake customers, opportunities across pipeline stages, dashboard metrics, WhatsApp conversations, and notifications. Keep the seed deterministic, clearly labeled as fictional, and scoped to the demo database. No promotional dataset is seeded here.
