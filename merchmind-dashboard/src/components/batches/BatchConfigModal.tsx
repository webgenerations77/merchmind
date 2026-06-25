import { useState } from 'react';
import type { BatchConfig } from '../../api/batches';

const TREND_SOURCES = [
  { key: 'google_trends', label: 'Google Trends' },
  { key: 'reddit', label: 'Reddit' },
  { key: 'twitter', label: 'Twitter / X' },
  { key: 'seasonal', label: 'Seasonal Calendar' },
];

const PRODUCT_TYPES = [
  { key: 'tshirt', label: 'T-Shirt' },
  { key: 'hoodie', label: 'Hoodie' },
  { key: 'long_sleeve', label: 'Long Sleeve' },
];

const EST_COST_PER_DESIGN = 0.015;

export default function BatchConfigModal({ onRun, onClose }: { onRun: (config: BatchConfig) => void; onClose: () => void }) {
  const [numDesigns, setNumDesigns] = useState(25);
  const [sources, setSources] = useState<Set<string>>(new Set(TREND_SOURCES.map((s) => s.key)));
  const [styleFilter, setStyleFilter] = useState('');
  const [productFocus, setProductFocus] = useState<Set<string>>(new Set());

  const toggleSource = (key: string) => {
    setSources((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const toggleProduct = (key: string) => {
    setProductFocus((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const estimatedCost = numDesigns * EST_COST_PER_DESIGN;

  const handleRun = () => {
    const config: BatchConfig = { num_designs: numDesigns };
    if (sources.size < TREND_SOURCES.length) {
      config.trend_sources = Array.from(sources);
    }
    if (styleFilter.trim()) {
      config.style_filter = styleFilter.trim();
    }
    if (productFocus.size > 0) {
      config.product_focus = Array.from(productFocus);
    }
    onRun(config);
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-bg-secondary border border-border rounded-2xl w-full max-w-lg p-6 space-y-5" onClick={(e) => e.stopPropagation()}>
        <div>
          <h2 className="text-xl font-bold text-text-primary">Run Batch</h2>
          <p className="text-sm text-text-secondary mt-1">Configure the batch pipeline before running.</p>
        </div>

        {/* Number of designs */}
        <div>
          <label className="block text-sm font-medium text-text-primary mb-2">Number of Designs</label>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setNumDesigns(Math.max(1, numDesigns - 1))}
              className="w-8 h-8 rounded-lg bg-bg-tertiary border border-border text-text-primary flex items-center justify-center hover:bg-bg-tertiary/80"
            >
              −
            </button>
            <input
              type="number"
              value={numDesigns}
              onChange={(e) => setNumDesigns(Math.max(1, Math.min(50, parseInt(e.target.value) || 1)))}
              className="w-20 text-center bg-bg-tertiary border border-border rounded-lg px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:border-accent"
              min={1}
              max={50}
            />
            <button
              onClick={() => setNumDesigns(Math.min(50, numDesigns + 1))}
              className="w-8 h-8 rounded-lg bg-bg-tertiary border border-border text-text-primary flex items-center justify-center hover:bg-bg-tertiary/80"
            >
              +
            </button>
            <span className="text-xs text-text-tertiary ml-2">~${EST_COST_PER_DESIGN.toFixed(3)}/design (Haiku scoring + Flux image)</span>
          </div>
        </div>

        {/* Trend sources */}
        <div>
          <label className="block text-sm font-medium text-text-primary mb-2">Trend Sources</label>
          <div className="flex flex-wrap gap-2">
            {TREND_SOURCES.map((s) => (
              <button
                key={s.key}
                onClick={() => toggleSource(s.key)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                  sources.has(s.key)
                    ? 'bg-accent/15 border-accent/40 text-accent'
                    : 'bg-bg-tertiary border-border text-text-tertiary hover:text-text-secondary'
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>
          {sources.size === 0 && (
            <p className="text-xs text-confidence-low mt-1">Select at least one source</p>
          )}
        </div>

        {/* Style filter */}
        <div>
          <label className="block text-sm font-medium text-text-primary mb-2">Style Direction <span className="text-text-tertiary font-normal">(optional)</span></label>
          <input
            type="text"
            value={styleFilter}
            onChange={(e) => setStyleFilter(e.target.value)}
            placeholder='e.g. "summer vibes", "Halloween", "minimalist"'
            className="w-full bg-bg-tertiary border border-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder-text-tertiary focus:outline-none focus:border-accent"
          />
        </div>

        {/* Product type focus */}
        <div>
          <label className="block text-sm font-medium text-text-primary mb-2">Product Focus <span className="text-text-tertiary font-normal">(optional — default: all types)</span></label>
          <div className="flex flex-wrap gap-2">
            {PRODUCT_TYPES.map((p) => (
              <button
                key={p.key}
                onClick={() => toggleProduct(p.key)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                  productFocus.has(p.key)
                    ? 'bg-accent/15 border-accent/40 text-accent'
                    : 'bg-bg-tertiary border-border text-text-tertiary hover:text-text-secondary'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Cost estimate */}
        <div className="bg-bg-tertiary rounded-xl p-4 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-text-primary">Estimated Cost</p>
            <p className="text-xs text-text-tertiary mt-0.5">{numDesigns} designs × ${EST_COST_PER_DESIGN.toFixed(3)}</p>
          </div>
          <p className="text-2xl font-bold text-text-primary">${estimatedCost.toFixed(2)}</p>
        </div>

        {/* Actions */}
        <div className="flex gap-3 justify-end pt-2">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-bg-tertiary border border-border text-text-secondary text-sm font-medium hover:text-text-primary transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleRun}
            disabled={sources.size === 0}
            className="px-5 py-2 rounded-lg bg-accent text-white font-semibold text-sm hover:bg-accent/80 transition-colors disabled:opacity-50"
          >
            Run Batch
          </button>
        </div>
      </div>
    </div>
  );
}
