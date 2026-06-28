export default function EmptyCatalog({ className = 'w-full h-full' }: { className?: string }) {
  return (
    <svg viewBox="0 0 160 160" fill="none" className={className} role="img" aria-label="Empty catalog">
      <path
        d="M54 54 L98 54 L120 76 C123 79 123 81 120 84 L84 120 C81 123 79 123 76 120 L54 98 Z"
        className="stroke-text-tertiary" strokeWidth="3" strokeLinejoin="round"
      />
      <circle cx="70" cy="70" r="6" className="fill-mint" />
      <circle cx="116" cy="116" r="14" className="fill-violet" />
      <path d="M116 110 V122 M110 116 H122" className="stroke-white" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}
