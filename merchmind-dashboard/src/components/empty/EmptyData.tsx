export default function EmptyData({ className = 'w-full h-full' }: { className?: string }) {
  return (
    <svg viewBox="0 0 160 160" fill="none" className={className} role="img" aria-label="No data yet">
      <line x1="36" y1="118" x2="124" y2="118" className="stroke-text-tertiary" strokeWidth="3" strokeLinecap="round" />
      <rect x="48" y="92" width="16" height="26" rx="3" className="stroke-text-tertiary" strokeWidth="2.5" />
      <rect x="72" y="74" width="16" height="44" rx="3" className="stroke-text-tertiary" strokeWidth="2.5" />
      <rect x="96" y="84" width="16" height="34" rx="3" className="stroke-text-tertiary" strokeWidth="2.5" />
      <path d="M44 100 L72 80 L100 88 L120 54" className="stroke-mint" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="120" cy="54" r="6" className="fill-mint" />
    </svg>
  );
}
