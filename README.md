# Lodol Docs

Documentation site for Lodol, built with [Next.js](https://nextjs.org/) and [Fumadocs](https://fumadocs.vercel.app/).

## Prerequisites

- Node.js 18+
- npm

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

## Project Structure

```
content/       — MDX documentation pages
app/           — Next.js app router pages and layouts
lib/           — Shared utilities and configuration
source.config.ts — Fumadocs MDX source configuration
```
