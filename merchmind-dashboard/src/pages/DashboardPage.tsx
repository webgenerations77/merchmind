import { useEffect, useState, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { listAlerts, resolveAlert } from '../api/alerts';
import { listBatches } from '../api/batches';
import { listProducts } from '../api/products';
import { getReviewQueue, getFeaturedDesigns, toggleFeatured } from '../api/designs';
import type { AlertOut, BatchOut, ProductOut, DesignQueueItem } from '../types/api';
import StatusBadge from '../components/shared/StatusBadge';
import ConfidenceBadge from '../components/shared/ConfidenceBadge';
import { formatTimeAgo, formatProductType, formatDate, toTitleCase } from '../utils/formatters';

export default function DashboardPage() {
  const [alerts, setAlerts] = useState<AlertOut[]>([]);
  const [batches, setBatches] = useState<BatchOut[]>([]);
  const [products, setProducts] = useState<ProductOut[]>([]);
  const [featured, setFeatured] = useState<DesignQueueItem[]>([]);
  const [queueCount, setQueueCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const loadData = useCallback(() => {
    Promise.all([
      listAlerts(false).then(setAlerts),
      listBatches().then(setBatches),
      listProducts().then(setProducts),
      getReviewQueue().then((q) => setQueueCount(q.length)).catch(() => null),
      getFeaturedDesigns().then(setFeatured).catch(() => null),
    ]).finally(() => setLoading(false));
  }, []);

  const handleUnfeature = async (id: string) => {
    await toggleFeatured(id);
    setFeatured((f) => f.filter((d) => d.id !== id));
  };

  useEffect(() => { loadData(); }, [loadData]);

  useEffect(() => {
    const latestBatch = batches[0];
    if (latestBatch?.status === 'running') {
      const interval = setInterval(loadData, 10000);
      return () => clearInterval(interval);
    }
  }, [batches, loadData]);

  const handleResolve = async (id: string) => {
    await resolveAlert(id);
    setAlerts((a) => a.filter((al) => al.id !== id));
  };

  const latestBatch = batches[0];
  const pendingProducts = products.filter((p) => p.publish_status === 'pending').length;

  if (loading) return <div className="flex items-center justify-center h-64 text-text-secondary">Loading...</div>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-text-primary">Dashboard</h1>

      {latestBatch?.status === 'running' && (
        <div className="p-4 bg-bg-secondary border border-accent/30 rounded-xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 rounded-full bg-accent animate-pulse" />
              <div>
                <p className="text-accent font-semibold">Batch in progress</p>
                <p className="text-sm text-text-secondary mt-0.5">
                  Generating designs — {latestBatch.total_ideas} trends scored, {products.length} products so far
                </p>
              </div>
            </div>
            <Link to="/review" className="px-3 py-1.5 rounded-lg bg-accent/20 text-accent text-sm font-medium hover:bg-accent/30 transition-colors">
              View progress
            </Link>
          </div>
        </div>
      )}

      {latestBatch?.status === 'complete' && queueCount > 0 && (
        <Link
          to="/review"
          className="block p-4 bg-approve/10 border border-approve/30 rounded-xl hover:bg-approve/15 transition-colors"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-approve font-semibold">Designs ready for review</p>
              <p className="text-sm text-text-secondary mt-0.5">
                {queueCount} designs waiting for your approval
              </p>
            </div>
            <span className="text-approve text-2xl font-bold">{queueCount}</span>
          </div>
        </Link>
      )}

      {featured.length > 0 && (
        <div className="bg-gradient-to-r from-confidence-medium/10 via-confidence-medium/5 to-transparent border border-confidence-medium/30 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-confidence-medium flex items-center justify-center">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white" className="w-3.5 h-3.5">
                  <path fillRule="evenodd" d="M10.788 3.21c.448-1.077 1.976-1.077 2.424 0l2.082 5.006 5.404.434c1.164.093 1.636 1.545.749 2.305l-4.117 3.527 1.257 5.273c.271 1.136-.964 2.033-1.96 1.425L12 18.354 7.373 21.18c-.996.608-2.231-.29-1.96-1.425l1.257-5.273-4.117-3.527c-.887-.76-.415-2.212.749-2.305l5.404-.434 2.082-5.005Z" clipRule="evenodd" />
                </svg>
              </span>
              <h2 className="text-lg font-bold text-confidence-medium">Featured</h2>
              <span className="text-xs text-confidence-medium/60 bg-confidence-medium/10 px-2 py-0.5 rounded-full">{featured.length}</span>
            </div>
            <Link to="/review" className="text-xs text-confidence-medium hover:text-confidence-medium transition-colors">
              Review all &rarr;
            </Link>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {featured.map((item) => (
              <div
                key={item.id}
                className="group relative bg-bg-secondary border border-border rounded-lg overflow-hidden hover:border-confidence-medium/50 transition-all cursor-pointer"
                onClick={() => navigate('/review', { state: { openDesignId: item.id, from: '/' } })}
              >
                <div className="relative aspect-square bg-bg-tertiary">
                  {(item.primary_mockup_url || item.processed_image_url) ? (
                    <img
                      src={item.primary_mockup_url || item.processed_image_url!}
                      alt={item.concept_name}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-text-tertiary text-xs">
                      Text Only
                    </div>
                  )}
                  <button
                    onClick={(e) => { e.stopPropagation(); handleUnfeature(item.id); }}
                    className="absolute top-1.5 right-1.5 w-6 h-6 rounded-full bg-confidence-medium text-white flex items-center justify-center shadow-lg shadow-confidence-medium/30 hover:bg-confidence-medium transition-colors"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-3 h-3">
                      <path fillRule="evenodd" d="M10.788 3.21c.448-1.077 1.976-1.077 2.424 0l2.082 5.006 5.404.434c1.164.093 1.636 1.545.749 2.305l-4.117 3.527 1.257 5.273c.271 1.136-.964 2.033-1.96 1.425L12 18.354 7.373 21.18c-.996.608-2.231-.29-1.96-1.425l1.257-5.273-4.117-3.527c-.887-.76-.415-2.212.749-2.305l5.404-.434 2.082-5.005Z" clipRule="evenodd" />
                    </svg>
                  </button>
                  <div className="absolute bottom-1.5 left-1.5">
                    <StatusBadge status={item.status} />
                  </div>
                </div>
                <div className="p-2">
                  <p className="text-xs font-semibold text-text-primary leading-tight line-clamp-1">
                    {toTitleCase(item.concept_name)}
                  </p>
                  <div className="flex items-center gap-1.5 mt-1">
                    <ConfidenceBadge score={item.quality_score} />
                    {(item.product_count ?? 0) > 0 && (
                      <span className="text-[10px] text-text-tertiary">{item.product_count} products</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link to="/products" className="bg-bg-secondary border border-border rounded-xl p-4 hover:border-accent/50 transition-colors cursor-pointer">
          <p className="text-xs text-text-tertiary">Total Products</p>
          <p className="text-2xl font-bold text-text-primary mt-1">{products.length}</p>
        </Link>
        <Link to="/products" state={{ filterStatus: 'pending' }} className="bg-bg-secondary border border-border rounded-xl p-4 hover:border-confidence-medium/50 transition-colors cursor-pointer">
          <p className="text-xs text-text-tertiary">Pending Publish</p>
          <p className="text-2xl font-bold text-confidence-medium mt-1">{pendingProducts}</p>
        </Link>
        <Link to="/batches" className="bg-bg-secondary border border-border rounded-xl p-4 hover:border-accent/50 transition-colors cursor-pointer">
          <p className="text-xs text-text-tertiary">Total Batches</p>
          <p className="text-2xl font-bold text-text-primary mt-1">{batches.length}</p>
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <h2 className="text-lg font-semibold text-text-primary mb-3">Active Alerts</h2>
          {alerts.length === 0 ? (
            <div className="bg-bg-secondary border border-border rounded-xl p-6 text-center text-text-tertiary text-sm">
              No active alerts
            </div>
          ) : (
            <div className="space-y-2">
              {alerts.map((alert) => (
                <div key={alert.id} className="bg-bg-secondary border border-border rounded-lg p-3 flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <StatusBadge status={alert.severity} />
                      <span className="text-xs text-text-tertiary">{formatTimeAgo(alert.created_at)}</span>
                    </div>
                    <p className="text-sm text-text-secondary">{alert.message}</p>
                  </div>
                  <button
                    onClick={() => handleResolve(alert.id)}
                    className="px-2 py-1 rounded text-xs text-text-tertiary hover:text-approve hover:bg-approve/10 transition-colors shrink-0"
                  >
                    Resolve
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div>
          <h2 className="text-lg font-semibold text-text-primary mb-3">Recent Products</h2>
          {products.length === 0 ? (
            <div className="bg-bg-secondary border border-border rounded-xl p-6 text-center text-text-tertiary text-sm">
              No products yet
            </div>
          ) : (
            <div className="space-y-2">
              {products.slice(0, 8).map((product) => (
                <div
                  key={product.id}
                  onClick={() => navigate('/products', { state: { selectedId: product.id, from: '/' } })}
                  className="bg-bg-secondary border border-border rounded-lg p-3 flex items-center gap-3 cursor-pointer hover:border-accent/50 transition-colors"
                >
                  <div className="w-10 h-10 rounded-md bg-bg-tertiary overflow-hidden shrink-0">
                    {(product.primary_mockup_url || product.processed_image_url) ? (
                      <img
                        src={product.primary_mockup_url || product.processed_image_url!}
                        alt={product.concept_name || product.product_type}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-text-tertiary text-[10px]">
                        {formatProductType(product.product_type).slice(0, 2)}
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-text-primary truncate">
                      {product.concept_name ? toTitleCase(product.concept_name) : formatProductType(product.product_type)}
                    </p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-xs text-text-tertiary">{formatProductType(product.product_type)}</span>
                      <span className="text-xs text-text-tertiary">{formatDate(product.created_at)}</span>
                    </div>
                  </div>
                  <StatusBadge status={product.publish_status} />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
