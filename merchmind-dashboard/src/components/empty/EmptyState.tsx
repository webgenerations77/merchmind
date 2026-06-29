import type { ReactNode } from 'react';

interface EmptyStateProps {
  illustration: ReactNode;
  heading: string;
  subtext?: string;
  action?: ReactNode;
}

export default function EmptyState({ illustration, heading, subtext, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center text-center gap-3 py-12">
      <div className="w-32 h-32">{illustration}</div>
      <h3 className="font-display font-semibold text-text-primary">{heading}</h3>
      {subtext && <p className="text-text-tertiary text-sm max-w-xs">{subtext}</p>}
      {action}
    </div>
  );
}
