import LogoMark from './LogoMark';
import Wordmark from './Wordmark';

interface LogoProps {
  markSize?: number;
  wordmarkClassName?: string;
  className?: string;
}

export default function Logo({
  markSize = 32,
  wordmarkClassName = 'text-xl',
  className = '',
}: LogoProps) {
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <LogoMark size={markSize} />
      <Wordmark className={wordmarkClassName} />
    </div>
  );
}
