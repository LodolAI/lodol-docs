# Lodol Docs

Documentation site for Lodol, built with [Next.js](https://nextjs.org/) and [Fumadocs](https://fumadocs.vercel.app/). It's served at [docs.lodol.com](https://docs.lodol.com).

## Prerequisites

- Node.js 18+
- npm
- Python 3 (used by the integrations reference renderer)

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
- `npm run generate-actions` — Regenerate the Integrations tab from
  `data/actions/`
- `npm test` — Run the Jest suite (TypeScript / React)
- `npm run test:watch` — Re-run tests on file change
- `npm run test:coverage` — Generate a coverage report
- `npm run test:python` — Run the Python tests for the integrations
  reference renderer (uses the standard-library `unittest` runner — no
  extra Python dependencies required)

## How the site is organized

The docs have three tabs, one per folder marked `"root": true` in
`content/docs/`:

| Tab | Folder | URL | What's in it |
| --- | --- | --- | --- |
| Documentation | `content/docs/(docs)/` | `/docs` | What Lodol is, building with an AI tool, concepts, and guides to the built-in steps |
| Integrations | `content/docs/integrations/` | `/docs/integrations` | Every app and built-in step, generated from `data/actions/` (see below) |
| API | `content/docs/api/` | `/docs/api` | The developer API: quickstart, authentication, errors, limits, endpoints, and the workflow format |

`(docs)` is a folder group: its name doesn't appear in URLs. Pages that
moved when the docs were reorganized redirect from their old addresses
(see `redirects` in `next.config.mjs`).

## Project Structure

```
content/docs/    — MDX documentation pages, one folder per tab
app/             — Next.js app router pages and layouts
components/      — The components pages use (see "Writing pages")
data/            — Generated/published data consumed at build time
                   (e.g. data/actions/ — see below)
lib/             — Shared utilities and configuration
scripts/         — Build-time generators
                   (e.g. scripts/render-actions-docs.py)
tests/ts/        — Jest tests for TypeScript code
tests/python/    — unittest tests for the integrations renderer
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

## Auto-generated integrations reference

The `content/docs/integrations/` directory is regenerated on every
build by `scripts/render-actions-docs.py`, and is `.gitignore`d — do not
edit those files by hand. From `data/actions/` the renderer writes:

- one page per app, at `/docs/integrations/<app>`;
- one page per group of Lodol's built-in steps (the `skipflow_*`
  providers), at `/docs/integrations/built-in/<name>`;
- the directory page and the `meta.json` files that order the sidebar;
- `catalog.json`, the list the directory searches and the counts the
  home page shows.

`data/actions/` is the public contract between the Lodol server
(closed-source) and these docs (open-source): one JSON file per
provider, named `<provider id>.json`. One file per provider keeps
each file far below GitHub's 100 MB limit, and keeps an update's diff
to the providers it changed. The files are published into
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

To preview locally with the current `data/actions/`, just run
`npm run dev` or `npm run generate-actions` directly.

## Writing pages

Every page leads with a one-sentence answer in its `description`, then
gets straight to it. A few conventions keep the docs consistent:

- **Write for the person building the workflow.** Second person, present
  tense, short sentences, sentence-case headings. Name things the way
  the product does: **bold** for what people see in Lodol (step names
  and field labels, such as **Request approval** and **Who to ask**),
  and `@payment.amount` for references to a value.
- **One running example.** The concept pages build on one workflow: a
  new Stripe payment adds a row to a Google sheet and posts in Slack.
  Reuse it where it fits rather than inventing a new scenario.
- **Only document what's true.** Check step names and fields against
  `data/actions/` or the product, and plan figures against
  [lodol.com/pricing](https://www.lodol.com/pricing).
- **End with where to go next**, usually a pair of `Cards`.

Besides Fumadocs' own components (`Cards`, `Callout`, `Steps`, `Tabs`,
`Accordions`), pages can use:

| Component | For |
| --- | --- |
| `<WorkflowPreview steps={[…]} />` | Drawing a workflow the way the editor lists it |
| `<Fields title="…">` with `<Field />` | Inputs, outputs, parameters and object fields |
| `<Endpoint method="POST" path="…" />` | An API endpoint's method and path |
| `<Example>` | An example that stays closed until it's wanted |

Code samples in more than one language use code-fence tabs, with
`tab-group="lang"` on the first block so the reader's choice carries
across pages. Inside `<Steps>`, give each `<Step>` a `###` heading:
`Step` doesn't render a title of its own.
