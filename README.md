# Lodol Docs

Documentation site for Lodol, built with [Next.js](https://nextjs.org/) and [Fumadocs](https://fumadocs.vercel.app/).

## Prerequisites

- Node.js 18+
- npm
- Python 3 (used by the actions API reference renderer)

## Getting Started

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

The site will be available at `https://localhost:3001`.

### Local HTTPS

The dev server uses `--experimental-https`, which automatically generates a local self-signed certificate on first run via Next.js. You may see a browser warning about the certificate being untrusted — this is expected for local development. Click through the warning to proceed.

If you run into certificate issues:

1. Delete the generated certificates in the project root (`certificates/` or `.next/` depending on your Next.js version) and restart the dev server to regenerate them.
2. On macOS, you may need to trust the certificate in Keychain Access, or launch Chrome with `--ignore-certificate-errors` for local testing.

## Scripts

- `npm run dev` — Start the development server with HTTPS on port 3001
- `npm run build` — Build for production
- `npm run start` — Start the production server
- `npm run lint` — Run ESLint
- `npm run generate-actions` — Regenerate the per-provider action MDX
  files from `data/actions.json`
- `npm test` — Run the Jest suite (TypeScript / React)
- `npm run test:watch` — Re-run tests on file change
- `npm run test:coverage` — Generate a coverage report
- `npm run test:python` — Run the Python tests for the actions docs
  renderer (uses the standard-library `unittest` runner — no extra
  Python dependencies required)

## Project Structure

```
content/         — MDX documentation pages
app/             — Next.js app router pages and layouts
data/            — Generated/published data consumed at build time
                   (e.g. data/actions.json — see below)
lib/             — Shared utilities and configuration
scripts/         — Build-time generators
                   (e.g. scripts/render-actions-docs.py)
tests/ts/        — Jest tests for TypeScript code
tests/python/    — unittest tests for the actions docs renderer
source.config.ts — Fumadocs MDX source configuration
```

## Testing

The TypeScript layer is covered by Jest + ts-jest with the `jsdom`
environment and React Testing Library. Tests live in `tests/ts/` and
run via `npm test`.

The Python `scripts/render-actions-docs.py` script is covered by
`unittest` tests in `tests/python/`. They run with the standard
library only — no extra Python dependencies — and can be invoked with
`npm run test:python`.

## Auto-generated API reference

The `content/docs/api-reference/actions/` directory is regenerated on
every build by `scripts/render-actions-docs.py`. The renderer reads
`data/actions.json` and emits one MDX page per provider plus an index
and `meta.json`. The directory is `.gitignore`d — do not edit those
files by hand.

`data/actions.json` is the public contract between the Lodol server
(closed-source) and these docs (open-source). It is published into
this repo as an automated pull request by the
`publish-action-specs` workflow in `lodolai/lodol` whenever the
server's provider library changes. To change what shows up in the
docs:

1. Update the relevant provider's `action_specs` in
   `lodolai/lodol`'s `projects/server/src/skipflow/integrations/providers/`.
2. Wait for the auto-PR to land here (or trigger
   `publish-action-specs` manually via workflow dispatch).
3. The next docs build picks up the change via the `predev` /
   `prebuild` npm hooks.

To preview locally with the current `data/actions.json`, just run
`npm run dev` or `npm run generate-actions` directly.
