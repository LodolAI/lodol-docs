import { icons, Box } from 'lucide-react';
import { cn } from '@/lib/cn';
import { AppMonogram, TILE_SIZES } from '@/components/app-monogram';

interface IntegrationIconProps {
  name: string;
  /** A lucide icon name, for Lodol's own built-in steps. */
  icon?: string;
  builtIn?: boolean;
  size?: keyof typeof TILE_SIZES;
  className?: string;
}

/**
 * The tile that stands for an integration: a built-in step's icon on
 * Lodol's violet, or an app's initials on a tint of its own.
 *
 * Server-only in practice: looking an icon up by name pulls in every lucide
 * icon, which a browser bundle shouldn't carry. Client code uses AppMonogram.
 */
export function IntegrationIcon({
  name,
  icon,
  builtIn = false,
  size = 'md',
  className,
}: IntegrationIconProps) {
  if (!builtIn) return <AppMonogram name={name} size={size} className={className} />;

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
