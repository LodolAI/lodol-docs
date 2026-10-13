import Image from 'next/image';
import { cn } from '@/lib/cn';
import { AppMonogram, TILE_SIZES } from '@/components/app-monogram';

// How big a logo sits inside each size of tile, in pixels.
const LOGO_SIZES = { sm: 22, md: 24, lg: 34 };

/**
 * An app's tile: its logo, or its initials when it has none. Logos sit on
 * white in both themes, since most are drawn for a light background.
 */
export function AppTile({
  name,
  logo,
  size = 'md',
  className,
}: {
  name: string;
  logo?: string;
  size?: keyof typeof TILE_SIZES;
  className?: string;
}) {
  if (!logo) return <AppMonogram name={name} size={size} className={className} />;
  const pixels = LOGO_SIZES[size];
  return (
    <span
      aria-hidden="true"
      className={cn(
        'inline-flex shrink-0 items-center justify-center border border-black/[0.06] bg-white dark:border-white/10',
        TILE_SIZES[size],
        className,
      )}
    >
      <Image src={logo} alt="" width={pixels} height={pixels} className="object-contain" />
    </span>
  );
}
