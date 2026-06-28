interface LogoMarkProps {
  size?: number;
  className?: string;
}

export default function LogoMark({ size = 40, className = '' }: LogoMarkProps) {
  const showSpokes = size >= 30;
  const useCircleCore = size < 20;

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 120 120"
      fill="none"
      className={className}
      role="img"
      aria-label="MerchMind"
    >
      <path
        d="M60 12 L101.6 36 L101.6 84 L60 108 L18.4 84 L18.4 36 Z"
        className="stroke-violet dark:stroke-violet-300"
        strokeWidth="4"
        strokeLinejoin="round"
      />
      {showSpokes && (
        <g className="stroke-violet dark:stroke-violet-300" strokeWidth="2" opacity="0.4">
          <line x1="60" y1="12" x2="60" y2="40" />
          <line x1="101.6" y1="36" x2="77.3" y2="50" />
          <line x1="101.6" y1="84" x2="77.3" y2="70" />
          <line x1="60" y1="108" x2="60" y2="80" />
          <line x1="18.4" y1="84" x2="42.7" y2="70" />
          <line x1="18.4" y1="36" x2="42.7" y2="50" />
        </g>
      )}
      {useCircleCore ? (
        <circle cx="60" cy="60" r="14" className="fill-mint" />
      ) : (
        <path
          d="M60 40 L77.3 50 L77.3 70 L60 80 L42.7 70 L42.7 50 Z"
          className="fill-mint"
        />
      )}
    </svg>
  );
}
