export default function EmptyCanvas({ className = 'w-full h-full' }: { className?: string }) {
  return (
    <svg viewBox="0 0 160 160" fill="none" className={className} role="img" aria-label="Empty canvas">
      <rect x="34" y="30" width="92" height="100" rx="6" className="stroke-text-tertiary" strokeWidth="3" />
      <path
        d="M64 58 L72 52 L88 52 L96 58 L104 66 L96 74 L92 70 L92 104 L68 104 L68 70 L64 74 L56 66 Z"
        className="stroke-violet" strokeWidth="2.5" strokeLinejoin="round" opacity="0.5"
      />
      <path d="M112 40 L115 49 L124 52 L115 55 L112 64 L109 55 L100 52 L109 49 Z" className="fill-mint" />
      <circle cx="118" cy="118" r="5" className="fill-violet" />
    </svg>
  );
}
