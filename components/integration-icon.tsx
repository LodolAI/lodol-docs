import { icons, Box } from 'lucide-react';
import { cn } from '@/lib/cn';
import { TILE_SIZES } from '@/components/app-monogram';
import { AppTile } from '@/components/app-tile';

interface IntegrationIconProps {
  name: string;
  /** A lucide icon name, for Lodol's own built-in steps. */
  icon?: string;
  /** An app's logo. Without one, the app shows its initials. */
  logo?: string;
  builtIn?: boolean;
  size?: keyof typeof TILE_SIZES;
  className?: string;
}

/**
 * The tile that stands for an integration: a built-in step's icon on
 * Lodol's violet, or an app's logo.
 *
 * Server-only in practice: looking an icon up by name pulls in every lucide
 * icon, which a browser bundle shouldn't carry. Client code uses AppTile.
 */
export function IntegrationIcon({
  name,
  icon,
  logo,
  builtIn = false,
  size = 'md',
  className,
}: IntegrationIconProps) {
  if (!builtIn) return <AppTile name={name} logo={logo} size={size} className={className} />;

  const Icon = (icon && icons[icon as keyof typeof icons]) || Box;
  return (
    <span
      aria-hidden="true"
      className={cn(
        'inline-flex shrink-0 items-center justify-center border border-brand/15 bg-brand-soft text-brand dark:border-brand-lilac/15 dark:bg-brand/20 dark:text-brand-lilac',
        TILE_SIZES[size],
        className,
      )}
    >
      <Icon strokeWidth={1.9} />
    </span>
  );
}
