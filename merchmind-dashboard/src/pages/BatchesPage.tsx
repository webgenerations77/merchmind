import { useEffect, useState } from 'react';
import { listBatches, triggerBatch } from '../api/batches';
import type { BatchOut } from '../types/api';
import StatusBadge from '../components/shared/StatusBadge';
import { formatDate, formatTimeAgo } from '../utils/formatters';

export default function BatchesPage() {
  const [batches, setBatches] = useState<BatchOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const load = () => listBatches().then(setBatches).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const handleTrigger = async () => {
    if (!confirm('Run a new batch now? This will scrape trends, score them, and generate designs.')) return;
    setTriggering(true);
    try {
      await triggerBatch();
      setTimeout(load, 3000);
    } catch { /* ignore */ }
    setTriggering(false);
  };

  if (loading) return <div className="flex items-center justify-center h-64 text-text-secondary">Loading...</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Batches</h1>
          <p className="text-sm text-text-secondary mt-1">{batches.length} batch runs</p>
        </div>
        <button
          onClick={handleTrigger}
          disabled={triggering}
          className="px-4 py-2 rounded-lg bg-accent text-white font-semibold text-sm hover:bg-accent/80 transition-colors disabled:opacity-50"
        >
          {triggering ? 'Triggering...' : 'Run Batch Now'}
        </button>
      </div>

      <div className="bg-bg-secondary border border-border rounded-xl overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left px-4 py-3 text-xs text-text-tertiary font-medium">Week</th>
              <th className="text-left px-4 py-3 text-xs text-text-tertiary font-medium">Status</th>
              <th className="text-left px-4 py-3 text-xs text-text-tertiary font-medium">Ideas</th>
              <th className="text-left px-4 py-3 text-xs text-text-tertiary font-medium">Queued</th>
              <th className="text-left px-4 py-3 text-xs text-text-tertiary font-medium">Duration</th>
              <th className="text-left px-4 py-3 text-xs text-text-tertiary font-medium">When</th>
            </tr>
          </thead>
          <tbody>
            {batches.map((batch) => {
              const duration = batch.run_completed_at
                ? `${Math.round((new Date(batch.run_completed_at).getTime() - new Date(batch.run_started_at).getTime()) / 1000)}s`
                : '...';
              return (
                <tr
                  key={batch.id}
                  className="border-b border-border last:border-b-0 hover:bg-bg-tertiary/50 cursor-pointer"
                  onClick={() => setExpandedId(expandedId === batch.id ? null : batch.id)}
                >
                  <td className="px-4 py-3 text-sm text-text-primary">{formatDate(batch.week_start)}</td>
                  <td className="px-4 py-3"><StatusBadge status={batch.status} /></td>
                  <td className="px-4 py-3 text-sm text-text-secondary">{batch.total_ideas}</td>
                  <td className="px-4 py-3 text-sm text-text-primary font-medium">{batch.queued_count}</td>
                  <td className="px-4 py-3 text-sm text-text-secondary">{duration}</td>
                  <td className="px-4 py-3 text-sm text-text-tertiary">{formatTimeAgo(batch.run_started_at)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {expandedId && (() => {
        const batch = batches.find((b) => b.id === expandedId);
        if (!batch || batch.error_log.length === 0) return null;
        return (
          <div className="mt-4 p-4 bg-bg-secondary border border-border rounded-xl">
            <h3 className="text-sm font-semibold text-text-primary mb-2">Error Log</h3>
            <div className="space-y-2">
              {batch.error_log.map((err, i) => (
                <div key={i} className="text-xs">
                  <span className="text-text-tertiary">{formatTimeAgo(err.time)}</span>
                  <span className="text-confidence-low ml-2">{err.error}</span>
                </div>
              ))}
            </div>
          </div>
        );
      })()}
    </div>
  );
}
