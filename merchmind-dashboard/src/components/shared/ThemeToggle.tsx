import { Sun, Moon } from 'lucide-react';
import { useThemeStore } from '../../stores/themeStore';

export default function ThemeToggle({ className = '' }: { className?: string }) {
  const theme = useThemeStore((s) => s.theme);
  const toggle = useThemeStore((s) => s.toggle);
  const isDark = theme === 'dark';

  return (
    <button
      onClick={toggle}
      aria-label={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
      className={`w-9 h-9 flex items-center justify-center rounded-lg text-text-secondary hover:text-text-primary hover:bg-bg-tertiary transition-colors ${className}`}
    >
      {isDark ? <Sun size={18} strokeWidth={2} /> : <Moon size={18} strokeWidth={2} />}
    </button>
  );
}
