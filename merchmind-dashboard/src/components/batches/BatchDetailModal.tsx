import { useEffect, useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { getBatchDetail, retryFailedItems } from '../../api/batches';
import apiClient from '../../api/client';
import type { BatchDetailOut, BatchItemOut } from '../../types/api';
import StatusBadge from '../shared/StatusBadge';
import { formatDate, formatTimeAgo, formatProductType } from '../../utils/formatters';

interface Props {
  batchId: string;
  onClose: () => void;
  onRefresh: () => void;
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  if (m < 60) return `${m}m ${s}s`;
  const h = Math.floor(m / 60);
  return `${h}h ${m % 60}m`;
}

function formatStep(step: string): string {
  const labels: Record<string, string> = {
    scoring: 'Trend Scoring',
    archetype: 'Archetype Classification',
    image_generation: 'Image Generation',
    quality: 'Quality Scoring',
    products: 'Product Creation',
    mockups: 'Mockup Generation',
    marketing: 'Marketing Assets',
    design_generation: 'Design Generation',
  };
  return labels[step] || step.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

export default function BatchDetailModal({ batchId, onClose, onRefresh }: Props) {
  const [detail, setDetail] = useState<BatchDetailOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [retrying, setRetrying] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [expandedItemId, setExpandedItemId] = useState<string | null>(null);

  useEffect(() => {
    getBatchDetail(batchId)
      .then(setDetail)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [batchId]);

  const handleRetry = async () => {
    if (!confirm('Retry all failed items? This will re-run image generation for each failed design.')) return;
    setRetrying(true);
    try {
      const result = await retryFailedItems(batchId);
      alert(result.message);
      const refreshed = await getBatchDetail(batchId);
      setDetail(refreshed);
      onRefresh();
    } catch {
      alert('Retry failed — check console for details.');
    }
    setRetrying(false);
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const resp = await apiClient.get(`/batches/${batchId}/export`, { responseType: 'blob' });
      const blob = new Blob([resp.data], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = resp.headers['content-disposition']?.match(/filename="(.+)"/)?.[1] || `batch_${batchId.slice(0, 8)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert('Export failed.');
    }
    setExporting(false);
  };

  if (loading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
        <div className="bg-bg-secondary rounded-2xl p-8 text-text-secondary">Loading...</div>
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
        <div className="bg-bg-secondary rounded-2xl p-8 text-text-secondary">Failed to load batch details.</div>
      </div>
    );
  }

  const { batch, items, success_count, failed_count } = detail;
  const elapsed = batch.run_completed_at
    ? (new Date(batch.run_completed_at).getTime() - new Date(batch.run_started_at).getTime()) / 1000
    : null;


  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        className="bg-bg-secondary border border-border rounded-2xl w-full max-w-3xl max-h-[85vh] flex flex-col shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-border">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-xl font-bold text-text-primary">
                Batch — {formatDate(batch.week_start)}
              </h2>
              <p className="text-sm text-text-tertiary mt-1">
                ID: {batch.id.slice(0, 8)}
              </p>
            </div>
            <button onClick={onClose} className="text-text-tertiary hover:text-text-primary text-2xl leading-none">&times;</button>
          </div>

          {/* Summary stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-4">
            <div className="bg-bg-tertiary rounded-lg p-3">
              <div className="text-xs text-text-tertiary">Status</div>
              <div className="mt-1">
                <StatusBadge status={batch.status} />
                {failed_count > 0 && success_count > 0 && (
                  <span className="text-xs text-confidence-low ml-2">with errors</span>
                )}
              </div>
            </div>
            <div className="bg-bg-tertiary rounded-lg p-3">
              <div className="text-xs text-text-tertiary">Started</div>
              <div className="text-sm text-text-primary mt-1">{formatTimeAgo(batch.run_started_at)}</div>
              <div className="text-xs text-text-tertiary">{new Date(batch.run_started_at).toLocaleString()}</div>
            </div>
            <div className="bg-bg-tertiary rounded-lg p-3">
              <div className="text-xs text-text-tertiary">Duration</div>
              <div className="text-sm text-text-primary mt-1">{elapsed ? formatDuration(elapsed) : 'Running...'}</div>
            </div>
            <div className="bg-bg-tertiary rounded-lg p-3">
              <div className="text-xs text-text-tertiary">Results</div>
              <div className="text-sm mt-1">
                <span className="text-approve font-semibold">{success_count}</span>
                <span className="text-text-tertiary"> / </span>
                {failed_count > 0 && (
                  <span className="text-confidence-low font-semibold">{failed_count}</span>
                )}
                {failed_count === 0 && (
                  <span className="text-text-tertiary">{failed_count}</span>
                )}
                <span className="text-text-tertiary"> / {items.length} total</span>
              </div>
            </div>
          </div>
        </div>

        {/* Items list */}
        <div className="flex-1 overflow-y-auto p-6">
          {items.length === 0 ? (
            <div className="text-center text-text-tertiary py-12">
              <p className="text-sm">No per-item data available for this batch.</p>
              <p className="text-xs mt-1">Item-level tracking was added after this batch ran.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {items.map((item) => (
                <BatchItemRow
                  key={item.id}
                  item={item}
                  expanded={expandedItemId === item.id}
                  onToggle={() => setExpandedItemId(expandedItemId === item.id ? null : item.id)}
                />
              ))}
            </div>
          )}

          {/* Error log fallback for old batches */}
          {items.length === 0 && batch.error_log.length > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-semibold text-text-primary mb-3">Error Log (Legacy)</h3>
              <div className="space-y-2">
                {batch.error_log.map((err, i) => (
                  <div key={i} className="text-xs bg-confidence-low/10 border border-confidence-low/20 rounded-lg p-3">
                    <span className="text-text-tertiary">{formatTimeAgo(err.time)}</span>
                    <span className="text-confidence-low ml-2">{err.error}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Actions footer */}
        <div className="p-4 border-t border-border flex items-center gap-3">
          {failed_count > 0 && (
            <button
              onClick={handleRetry}
              disabled={retrying}
              className="px-4 py-2 rounded-lg bg-confidence-low text-white font-semibold text-sm hover:bg-confidence-low/80 transition-colors disabled:opacity-50"
            >
              {retrying ? 'Retrying...' : `Retry Failed Items (${failed_count})`}
            </button>
          )}
          <button
            onClick={handleExport}
            disabled={exporting}
            className="px-4 py-2 rounded-lg bg-bg-tertiary text-text-primary font-semibold text-sm hover:bg-border transition-colors disabled:opacity-50"
          >
            {exporting ? 'Exporting...' : 'Export Log'}
          </button>
          <div className="flex-1" />
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-bg-tertiary text-text-secondary text-sm hover:bg-border transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}


function BatchItemRow({ item, expanded, onToggle }: { item: BatchItemOut; expanded: boolean; onToggle: () => void }) {
  const duration = item.started_at && item.completed_at
    ? (new Date(item.completed_at).getTime() - new Date(item.started_at).getTime()) / 1000
    : null;

  const isFailed = item.status === 'failed';

  return (
    <div className={`rounded-lg border ${isFailed ? 'border-confidence-low/30 bg-confidence-low/5' : 'border-border bg-bg-tertiary/50'}`}>
      <div
        className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-bg-tertiary/80 rounded-lg transition-colors"
        onClick={onToggle}
      >
        <span className="text-lg flex-shrink-0">{isFailed ? '❌' : item.status === 'running' ? '⏳' : '✅'}</span>

        {item.processed_image_url && (
          <img
            src={item.processed_image_url}
            alt=""
            className="w-8 h-8 rounded object-cover flex-shrink-0"
          />
        )}

        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-text-primary truncate">{item.concept_name}</div>
          {isFailed && item.failed_step && (
            <div className="text-xs text-confidence-low mt-0.5">
              Failed at: {formatStep(item.failed_step)}
            </div>
          )}
          {!isFailed && item.product_types.length > 0 && (
            <div className="text-xs text-text-tertiary mt-0.5">
              {item.product_types.map(formatProductType).join(', ')}
            </div>
          )}
        </div>

        {duration !== null && (
          <span className="text-xs text-text-tertiary flex-shrink-0">{formatDuration(duration)}</span>
        )}

        <ChevronDown size={18} strokeWidth={2} className={`text-text-tertiary transition-transform ${expanded ? 'rotate-180' : ''}`} />
      </div>

      {expanded && (
        <div className="px-4 pb-3 pt-1 border-t border-border/50">
          {isFailed && item.error_summary && (
            <div className="mb-2">
              <div className="text-xs font-semibold text-confidence-low mb-1">Error</div>
              <div className="text-sm text-text-primary">{item.error_summary}</div>
            </div>
          )}
          {isFailed && item.error_detail && (
            <details className="mt-2">
              <summary className="text-xs text-text-tertiary cursor-pointer hover:text-text-secondary">
                Full stack trace
              </summary>
              <pre className="mt-1 text-xs text-text-tertiary bg-bg-primary rounded p-2 overflow-x-auto max-h-48 overflow-y-auto whitespace-pre-wrap">
                {item.error_detail}
              </pre>
            </details>
          )}
          {!isFailed && (
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
              {item.product_types.length > 0 && (
                <>
                  <span className="text-text-tertiary">Products</span>
                  <span className="text-text-primary">{item.product_types.map(formatProductType).join(', ')}</span>
                </>
              )}
              <span className="text-text-tertiary">Started</span>
              <span className="text-text-primary">{new Date(item.started_at).toLocaleTimeString()}</span>
              {item.completed_at && (
                <>
                  <span className="text-text-tertiary">Completed</span>
                  <span className="text-text-primary">{new Date(item.completed_at).toLocaleTimeString()}</span>
                </>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
