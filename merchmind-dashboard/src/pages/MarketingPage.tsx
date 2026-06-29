import { useEffect, useState } from 'react';
import { listMarketingAssets, type MarketingAsset } from '../api/marketing';
import StatusBadge from '../components/shared/StatusBadge';
import ClickableImage from '../components/shared/ClickableImage';
import { formatTimeAgo } from '../utils/formatters';
import EmptyState from '../components/empty/EmptyState';
import EmptyData from '../components/empty/EmptyData';

const CHANNELS = ['all', 'instagram', 'tiktok', 'pinterest', 'email', 'blog'] as const;

const CHANNEL_ICONS: Record<string, string> = {
  instagram: 'IG',
  tiktok: 'TT',
  pinterest: 'PN',
  email: 'EM',
  blog: 'BG',
};

function AssetCard({ asset, onSelect }: { asset: MarketingAsset; onSelect: () => void }) {
  const caption = asset.content?.caption || asset.content?.subject || asset.content?.title || '';
  const hashtags = asset.content?.hashtags || '';

  return (
    <button onClick={onSelect} className="bg-bg-secondary border border-border rounded-xl p-4 text-left hover:border-accent/50 transition-colors w-full">
      <div className="flex items-start gap-3">
        {asset.design_image && (
          <img src={asset.design_image} alt="" className="w-14 h-14 rounded-lg object-cover shrink-0" />
        )}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-bold text-accent uppercase">{CHANNEL_ICONS[asset.channel] || asset.channel}</span>
            <span className="text-xs text-text-tertiary">{asset.design_name}</span>
            <StatusBadge status={asset.status} />
          </div>
          <p className="text-sm text-text-primary line-clamp-2">{caption}</p>
          {hashtags && <p className="text-xs text-accent mt-1 truncate">{hashtags}</p>}
          <p className="text-xs text-text-tertiary mt-1">{formatTimeAgo(asset.created_at)}</p>
        </div>
      </div>
    </button>
  );
}

function AssetDetail({ asset, onBack }: { asset: MarketingAsset; onBack: () => void }) {
  return (
    <div>
      <button onClick={onBack} className="text-text-secondary hover:text-text-primary text-sm mb-4">
        &larr; Back to marketing
      </button>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-bg-secondary border border-border rounded-xl p-5">
            <div className="flex items-center gap-3 mb-4">
              <span className="text-lg font-bold text-accent uppercase">{asset.channel}</span>
              <StatusBadge status={asset.status} />
              {asset.design_name && <span className="text-sm text-text-secondary">{asset.design_name}</span>}
            </div>

            {Object.entries(asset.content || {}).map(([key, value]) => (
              <div key={key} className="mb-4">
                <p className="text-xs text-text-tertiary uppercase mb-1">{key.replace(/_/g, ' ')}</p>
                <div className="bg-bg-tertiary rounded-lg p-3 relative group">
                  <p className="text-sm text-text-primary whitespace-pre-wrap">{value}</p>
                  <button
                    onClick={() => navigator.clipboard.writeText(String(value))}
                    className="absolute top-2 right-2 px-2 py-1 rounded bg-bg-secondary border border-border text-xs text-text-tertiary opacity-0 group-hover:opacity-100 transition-opacity hover:text-text-primary"
                  >
                    Copy
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          {asset.design_image && (
            <div className="bg-bg-secondary border border-border rounded-xl p-4">
              <ClickableImage src={asset.design_image} alt={asset.design_name || ''} className="w-full rounded-lg" />
            </div>
          )}
          <div className="bg-bg-secondary border border-border rounded-xl p-4">
            <p className="text-xs text-text-tertiary">Created</p>
            <p className="text-sm text-text-primary">{formatTimeAgo(asset.created_at)}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function MarketingPage() {
  const [assets, setAssets] = useState<MarketingAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [channel, setChannel] = useState<string>('all');
  const [selected, setSelected] = useState<MarketingAsset | null>(null);

  useEffect(() => {
    listMarketingAssets().then(setAssets).catch(() => null).finally(() => setLoading(false));
  }, []);

  if (selected) return <AssetDetail asset={selected} onBack={() => setSelected(null)} />;
  if (loading) return <div className="flex items-center justify-center h-64 text-text-secondary">Loading...</div>;

  const filtered = channel === 'all' ? assets : assets.filter((a) => a.channel === channel);

  const grouped: Record<string, MarketingAsset[]> = {};
  for (const a of filtered) {
    const key = a.design_id;
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(a);
  }

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Marketing</h1>
        <p className="text-sm text-text-secondary mt-1">Generated social media copy, email templates, and blog posts</p>
      </div>

      <div className="flex gap-1 bg-bg-secondary rounded-lg p-1 border border-border">
        {CHANNELS.map((ch) => (
          <button
            key={ch}
            onClick={() => setChannel(ch)}
            className={`flex-1 px-3 py-1.5 rounded-md text-xs font-medium transition-colors capitalize ${
              channel === ch ? 'bg-accent text-white' : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            {ch} {ch !== 'all' && `(${assets.filter((a) => a.channel === ch).length})`}
          </button>
        ))}
      </div>

      {Object.entries(grouped).length === 0 ? (
        <EmptyState
          illustration={<EmptyData />}
          heading="No marketing assets yet"
          subtext="Marketing copy is generated automatically when designs are created"
        />
      ) : (
        Object.entries(grouped).map(([designId, designAssets]) => (
          <div key={designId} className="space-y-2">
            <div className="flex items-center gap-3">
              {designAssets[0].design_image && (
                <img src={designAssets[0].design_image} alt="" className="w-8 h-8 rounded-lg object-cover" />
              )}
              <h3 className="text-sm font-semibold text-text-primary">{designAssets[0].design_name || 'Design'}</h3>
              <span className="text-xs text-text-tertiary">{designAssets.length} assets</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {designAssets.map((a) => (
                <AssetCard key={a.id} asset={a} onSelect={() => setSelected(a)} />
              ))}
            </div>
          </div>
        ))
      )}
    </div>
  );
}
