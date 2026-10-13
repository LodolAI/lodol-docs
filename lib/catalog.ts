import fs from 'node:fs';
import path from 'node:path';

/** One app or group of built-in steps, as the directory lists it. */
export interface CatalogEntry {
  id: string;
  name: string;
  description: string;
  href: string;
  actions: number;
  builtIn: boolean;
  /** A lucide icon name, for a built-in step group. */
  icon?: string;
}

export interface Catalog {
  apps: number;
  appActions: number;
  /** Ids of the apps the directory shows first. */
  popular: string[];
  entries: CatalogEntry[];
}

// Written by scripts/render-actions-docs.py, which `npm run dev` and
// `npm run build` run first.
const CATALOG_FILE = path.join(
  process.cwd(),
  'content',
  'docs',
  'integrations',
  'catalog.json',
);

let cached: Catalog | undefined;

export function getCatalog(): Catalog {
  if (!cached) {
    try {
      cached = JSON.parse(fs.readFileSync(CATALOG_FILE, 'utf8')) as Catalog;
    } catch (error) {
      throw new Error(
        `Couldn't read ${CATALOG_FILE}. Run \`npm run generate-actions\` to write it.`,
        { cause: error },
      );
    }
  }
  return cached;
}
