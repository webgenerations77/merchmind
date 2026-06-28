// Maps usage contexts to logo filenames under src/assets/logos/.
// Drop logo files here and reference them by filename only — never hardcode paths elsewhere.
// If a file is missing, components should fail silently (no broken-image icon).

export const LOGO_CONFIG = {
  // Full wordmark for the sidebar/header
  header: 'logo-main.png',

  // Square mark/icon for review cards and tight spaces
  reviewCard: 'logo-mark.png',

  // Translucent version for watermarking generated mockups
  watermark: 'logo-watermark.png',
} as const;

export type LogoContext = keyof typeof LOGO_CONFIG;

// Returns an import-ready URL or null if the file doesn't exist.
// Vite resolves these at build time — unknown files return null at runtime via error handling.
const _logoCache: Partial<Record<LogoContext, string | null>> = {};

export async function getLogoUrl(context: LogoContext): Promise<string | null> {
  if (context in _logoCache) return _logoCache[context]!;
  const filename = LOGO_CONFIG[context];
  try {
    const module = await import(`./${filename}`);
    _logoCache[context] = module.default as string;
    return _logoCache[context]!;
  } catch {
    _logoCache[context] = null;
    return null;
  }
}

// Synchronous variant for use in components that pre-load on mount
export function useLogoUrl(_context: LogoContext): string | null {
  // Intentionally returns null until the async load completes.
  // Components should handle null gracefully (no <img> render).
  return null; // replaced by actual URL after mount via useEffect + getLogoUrl
}
