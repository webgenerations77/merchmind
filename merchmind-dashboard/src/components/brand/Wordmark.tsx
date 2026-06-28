interface WordmarkProps {
  className?: string;
}

export default function Wordmark({ className = '' }: WordmarkProps) {
  return (
    <span className={`font-display font-bold tracking-[-0.02em] ${className}`}>
      <span className="text-text-primary">Merch</span>
      <span className="text-violet dark:text-violet-300">Mind</span>
    </span>
  );
}
