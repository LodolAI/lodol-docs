import type { CSSProperties } from 'react';
import { cn } from '@/lib/cn';

// Hues that read well as soft tints in both themes. An app's tile takes one
// by its name, so it keeps the same colour everywhere it appears.
const HUES = [262, 222, 199, 172, 142, 38, 16, 346, 290, 240];

function hueFor(name: string): number {
  let hash = 5381;
  for (const char of name) hash = ((hash << 5) + hash + char.codePointAt(0)!) | 0;
  return HUES[Math.abs(hash) % HUES.length];
}

/** "Google Sheets" → "GS", "Gmail" → "G": the first letter of up to two words. */
export function initialsFor(name: string): string {
  const words = name
    .split(/[\s\-–—/.&+]+/)
    .map((word) => word.replace(/[^\p{L}\p{N}]/gu, ''))
    .filter(Boolean);
  return words
    .slice(0, 2)
    .map((word) => word[0])
    .join('')
    .toUpperCase();
}

export const TILE_SIZES = {
  sm: 'size-9 rounded-lg text-[13px] [&_svg]:size-[18px]',
  md: 'size-10 rounded-xl text-sm [&_svg]:size-5',
  lg: 'size-14 rounded-2xl text-lg [&_svg]:size-7',
};

/** An app's tile: its initials on a tint of its own. */
export function AppMonogram({
  name,
  size = 'md',
  className,
}: {
  name: string;
  size?: keyof typeof TILE_SIZES;
  className?: string;
}) {
  return (
    <span
      aria-hidden="true"
      style={{ '--tile-h': hueFor(name) } as CSSProperties}
      className={cn(
        'inline-flex shrink-0 items-center justify-center border font-semibold tracking-tight',
        'border-[hsl(var(--tile-h)_55%_86%)] bg-[hsl(var(--tile-h)_85%_96%)] text-[hsl(var(--tile-h)_50%_34%)]',
        'dark:border-[hsl(var(--tile-h)_30%_28%)] dark:bg-[hsl(var(--tile-h)_28%_16%)] dark:text-[hsl(var(--tile-h)_75%_80%)]',
        TILE_SIZES[size],
        className,
      )}
    >
      {initialsFor(name)}
    </span>
  );
}
