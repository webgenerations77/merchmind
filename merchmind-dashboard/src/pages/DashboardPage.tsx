import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { listAlerts, resolveAlert } from '../api/alerts';
import { listBatches } from '../api/batches';
import { listProducts } from '../api/products';
import type { AlertOut, BatchOut, ProductOut } from '../types/api';
import StatusBadge from '../components/shared/StatusBadge';
import { formatTimeAgo, formatCurrency, formatProductType } from '../utils/formatters';

export default function DashboardPage() {
  const [alerts, setAlerts] = useState<AlertOut[]>([]);
  const [batches, setBatches] = useState<BatchOut[]>([]);
  const [products, setProducts] = useState<ProductOut[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    Promise.all([
      listAlerts(false).then(setAlerts),
      listBatches().then(setBatches),
      listProducts().then(setProducts),
    ]).finally(() => setLoading(false));
  }, []);

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

      {latestBatch && latestBatch.queued_count > 0 && (
        <Link
          to="/review"
          className="block p-4 bg-accent/10 border border-accent/30 rounded-xl hover:bg-accent/15 transition-colors"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-accent font-semibold">Designs ready for review</p>
              <p className="text-sm text-text-secondary mt-0.5">
                {latestBatch.queued_count} designs from batch {latestBatch.week_start}
              </p>
            </div>
            <span className="text-accent text-2xl font-bold">{latestBatch.queued_count}</span>
          </div>
        </Link>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-bg-secondary border border-border rounded-xl p-4">
          <p className="text-xs text-text-tertiary">Total Products</p>
          <p className="text-2xl font-bold text-text-primary mt-1">{products.length}</p>
        </div>
        <div className="bg-bg-secondary border border-border rounded-xl p-4">
          <p className="text-xs text-text-tertiary">Pending Publish</p>
          <p className="text-2xl font-bold text-confidence-medium mt-1">{pendingProducts}</p>
        </div>
        <div className="bg-bg-secondary border border-border rounded-xl p-4">
          <p className="text-xs text-text-tertiary">Total Batches</p>
          <p className="text-2xl font-bold text-text-primary mt-1">{batches.length}</p>
        </div>
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
                  onClick={() => navigate('/products', { state: { selectedId: product.id } })}
                  className="bg-bg-secondary border border-border rounded-lg p-3 flex items-center justify-between cursor-pointer hover:border-accent/50 transition-colors"
                >
                  <div>
                    <p className="text-sm text-text-primary">{formatProductType(product.product_type)}</p>
                    <p className="text-xs text-text-tertiary">{formatCurrency(product.retail_price)}</p>
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
