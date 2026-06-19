import { useEffect, useState } from 'react';
import { getSettings, updateSettings, listClusters } from '../api/settings';
import { getIntegrationHealth } from '../api/health';
import type { AppSettings, NicheCluster, IntegrationHealth } from '../types/api';
import { formatCurrency } from '../utils/formatters';

const PRODUCT_TYPES = ['tshirt', 'mug', 'hat', 'sticker', 'phone_case', 'poster'];

export default function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [clusters, setClusters] = useState<NicheCluster[]>([]);
  const [health, setHealth] = useState<IntegrationHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    Promise.all([
      getSettings().then(setSettings),
      listClusters().then(setClusters),
      getIntegrationHealth().then(setHealth).catch(() => null),
    ]).finally(() => setLoading(false));
  }, []);

  const save = async (updates: Partial<AppSettings>) => {
    setSaving(true);
    try {
      const updated = await updateSettings(updates);
      setSettings(updated);
    } catch { /* ignore */ }
    setSaving(false);
  };

  if (loading || !settings) return <div className="flex items-center justify-center h-64 text-text-secondary">Loading...</div>;

  return (
    <div className="space-y-6 max-w-3xl">
      <h1 className="text-2xl font-bold text-text-primary">Settings</h1>

      <section className="bg-bg-secondary border border-border rounded-xl p-5">
        <h2 className="text-base font-semibold text-text-primary mb-4">Quality Thresholds</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-text-tertiary">Quality Threshold</label>
            <input
              type="number" min={0} max={50} value={settings.quality_threshold}
              onChange={(e) => setSettings({ ...settings, quality_threshold: +e.target.value })}
              onBlur={() => save({ quality_threshold: settings.quality_threshold })}
              className="mt-1 w-full px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-sm text-text-primary"
            />
          </div>
          <div>
            <label className="text-xs text-text-tertiary">Score Threshold</label>
            <input
              type="number" min={0} max={100} value={settings.score_threshold}
              onChange={(e) => setSettings({ ...settings, score_threshold: +e.target.value })}
              onBlur={() => save({ score_threshold: settings.score_threshold })}
              className="mt-1 w-full px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-sm text-text-primary"
            />
          </div>
          <div>
            <label className="text-xs text-text-tertiary">Min Queue Size</label>
            <input
              type="number" min={1} max={50} value={settings.min_queue_size}
              onChange={(e) => setSettings({ ...settings, min_queue_size: +e.target.value })}
              onBlur={() => save({ min_queue_size: settings.min_queue_size })}
              className="mt-1 w-full px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-sm text-text-primary"
            />
          </div>
          <div>
            <label className="text-xs text-text-tertiary">Max Queue Size</label>
            <input
              type="number" min={1} max={50} value={settings.max_queue_size}
              onChange={(e) => setSettings({ ...settings, max_queue_size: +e.target.value })}
              onBlur={() => save({ max_queue_size: settings.max_queue_size })}
              className="mt-1 w-full px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-sm text-text-primary"
            />
          </div>
        </div>
        {saving && <p className="text-xs text-accent mt-2">Saving...</p>}
      </section>

      <section className="bg-bg-secondary border border-border rounded-xl p-5">
        <h2 className="text-base font-semibold text-text-primary mb-4">Pricing</h2>
        <div className="mb-4">
          <label className="text-xs text-text-tertiary">Trend Boost Max</label>
          <input
            type="number" step={0.01} min={0} max={1} value={settings.trend_boost_max}
            onChange={(e) => setSettings({ ...settings, trend_boost_max: +e.target.value })}
            onBlur={() => save({ trend_boost_max: settings.trend_boost_max })}
            className="mt-1 w-32 px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-sm text-text-primary"
          />
        </div>
        <div className="grid grid-cols-3 gap-3">
          {PRODUCT_TYPES.map((pt) => (
            <div key={pt}>
              <label className="text-xs text-text-tertiary capitalize">{pt.replace(/_/g, ' ')} Floor</label>
              <p className="text-sm text-text-primary mt-1">{formatCurrency(settings.floor_prices[pt] || 0)}</p>
              <p className="text-xs text-text-tertiary">Markup: {settings.base_markup[pt] || 0}x</p>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-bg-secondary border border-border rounded-xl p-5">
        <h2 className="text-base font-semibold text-text-primary mb-4">Niche Clusters</h2>
        {clusters.length === 0 ? (
          <p className="text-sm text-text-tertiary">No clusters configured</p>
        ) : (
          <div className="space-y-3">
            {clusters.map((cluster) => (
              <div key={cluster.id} className="flex items-center justify-between p-3 bg-bg-tertiary rounded-lg">
                <div className="flex items-center gap-3">
                  <span className="text-lg">{cluster.emoji}</span>
                  <div>
                    <p className="text-sm text-text-primary font-medium">{cluster.name}</p>
                    <p className="text-xs text-text-tertiary">{cluster.keywords.slice(0, 5).join(', ')}</p>
                  </div>
                </div>
                <span className={`text-xs font-medium ${cluster.active ? 'text-approve' : 'text-text-tertiary'}`}>
                  {cluster.active ? 'Active' : 'Inactive'}
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      {health && (
        <section className="bg-bg-secondary border border-border rounded-xl p-5">
          <h2 className="text-base font-semibold text-text-primary mb-4">Integration Health</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {Object.values(health.services).map((svc) => (
              <div key={svc.service} className="flex items-center gap-2 p-2 bg-bg-tertiary rounded-lg">
                <span className={`w-2 h-2 rounded-full ${svc.ok ? 'bg-approve' : 'bg-confidence-low'}`} />
                <span className="text-sm text-text-primary capitalize">{svc.service.replace(/_/g, ' ')}</span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
