import { useEffect, useState, useCallback } from 'react';
import { getUsageSummary, getUsageHistory, getApiBalances, type UsageSummary, type UsageLogEntry, type ApiBalanceResult } from '../api/apiUsage';
import { formatCurrency, formatCostPrecise } from '../utils/formatters';

const PERIODS = [
  { value: 'day', label: 'Today' },
  { value: 'week', label: 'This Week' },
  { value: 'month', label: 'This Month' },
  { value: 'all', label: 'All Time' },
];

const SERVICE_COLORS: Record<string, string> = {
  claude: 'text-accent',
  openai: 'text-approve',
  replicate: 'text-confidence-medium',
};

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    second: '2-digit',
    hour12: true,
  });
}

function CallHistoryPanel({ period, service, operation, onClose }: {
  period: string;
  service?: string;
  operation?: string;
  onClose: () => void;
}) {
  const [logs, setLogs] = useState<UsageLogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const pageSize = 50;

  useEffect(() => {
    setLoading(true);
    getUsageHistory(period, service, operation, pageSize, page * pageSize)
      .then((r) => { setLogs(r.logs); setTotal(r.total); })
      .catch(() => null)
      .finally(() => setLoading(false));
  }, [period, service, operation, page]);

  const title = service && operation
    ? `${service} / ${operation.replace(/_/g, ' ')}`
    : service
    ? service
    : 'All Calls';

  return (
    <section className="bg-bg-secondary border border-border rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-base font-semibold text-text-primary capitalize">{title}</h2>
          <p className="text-xs text-text-tertiary">{total} calls total</p>
        </div>
        <button onClick={onClose} className="px-3 py-1.5 rounded-lg bg-bg-tertiary border border-border text-sm text-text-secondary hover:text-text-primary transition-colors">
          Close
        </button>
      </div>

      {loading ? (
        <p className="text-center text-text-tertiary text-sm py-8">Loading...</p>
      ) : logs.length === 0 ? (
        <p className="text-center text-text-tertiary text-sm py-8">No calls found</p>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left px-3 py-2 text-xs text-text-tertiary font-medium">Time</th>
                  <th className="text-left px-3 py-2 text-xs text-text-tertiary font-medium">Service</th>
                  <th className="text-left px-3 py-2 text-xs text-text-tertiary font-medium">Operation</th>
                  <th className="text-left px-3 py-2 text-xs text-text-tertiary font-medium">Model</th>
                  <th className="text-right px-3 py-2 text-xs text-text-tertiary font-medium">Tokens</th>
                  <th className="text-right px-3 py-2 text-xs text-text-tertiary font-medium">Cost</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id} className="border-b border-border last:border-b-0 hover:bg-bg-tertiary/50">
                    <td className="px-3 py-2 text-xs text-text-secondary font-mono whitespace-nowrap">
                      {formatTimestamp(log.created_at)}
                    </td>
                    <td className={`px-3 py-2 text-sm capitalize ${SERVICE_COLORS[log.service] || 'text-text-primary'}`}>
                      {log.service}
                    </td>
                    <td className="px-3 py-2 text-sm text-text-secondary">{log.operation.replace(/_/g, ' ')}</td>
                    <td className="px-3 py-2 text-xs text-text-tertiary font-mono">{log.model || '-'}</td>
                    <td className="px-3 py-2 text-xs text-text-tertiary text-right whitespace-nowrap">
                      {log.input_tokens > 0
                        ? `${(log.input_tokens / 1000).toFixed(1)}K in / ${(log.output_tokens / 1000).toFixed(1)}K out`
                        : '-'}
                    </td>
                    <td className="px-3 py-2 text-sm font-medium text-text-primary text-right">
                      {formatCostPrecise(log.estimated_cost)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {total > pageSize && (
            <div className="flex items-center justify-between mt-3 pt-3 border-t border-border">
              <span className="text-xs text-text-tertiary">
                Showing {page * pageSize + 1}-{Math.min((page + 1) * pageSize, total)} of {total}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(Math.max(0, page - 1))}
                  disabled={page === 0}
                  className="px-2 py-1 rounded text-xs text-text-secondary hover:text-text-primary disabled:opacity-30"
                >
                  Prev
                </button>
                <button
                  onClick={() => setPage(page + 1)}
                  disabled={(page + 1) * pageSize >= total}
                  className="px-2 py-1 rounded text-xs text-text-secondary hover:text-text-primary disabled:opacity-30"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}

const SERVICE_LABELS: Record<string, string> = {
  anthropic: 'Anthropic (Claude)',
  openai: 'OpenAI (DALL-E)',
  replicate: 'Replicate (Flux)',
  printify: 'Printify',
};

const SERVICE_ICONS: Record<string, string> = {
  anthropic: '🧠',
  openai: '🎨',
  replicate: '⚡',
  printify: '🖨️',
};

function BalanceCards({ balances, onRefresh, refreshing }: { balances: ApiBalanceResult | null; onRefresh: () => void; refreshing: boolean }) {
  if (!balances) return null;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-text-primary">API Balances</h2>
        <div className="flex items-center gap-3">
          {balances.checked_at && (
            <span className="text-xs text-text-tertiary">
              Updated {new Date(balances.checked_at).toLocaleTimeString()}
            </span>
          )}
          <button
            onClick={onRefresh}
            disabled={refreshing}
            className="px-3 py-1.5 rounded-lg bg-bg-tertiary border border-border text-xs text-text-secondary hover:text-text-primary transition-colors disabled:opacity-50"
          >
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {balances.providers.map((p) => (
          <a
            key={p.service}
            href={p.console_url}
            target="_blank"
            rel="noopener noreferrer"
            className="bg-bg-secondary border border-border rounded-xl p-4 hover:border-accent/50 transition-colors group"
          >
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">{SERVICE_ICONS[p.service] || '🔌'}</span>
              <span className="text-sm font-medium text-text-primary capitalize">{SERVICE_LABELS[p.service] || p.service}</span>
            </div>
            {p.available ? (
              <div>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-approve/15 text-approve text-xs font-medium">
                  Connected
                </span>
                {p.spend && (
                  <div className="mt-2 space-y-1">
                    <p className="text-lg font-bold text-text-primary">{formatCostPrecise(p.spend.month_cost)}</p>
                    <p className="text-xs text-text-tertiary">{p.spend.month_calls} calls this month</p>
                    <p className="text-xs text-text-tertiary">All time: {formatCostPrecise(p.spend.total_cost)} ({p.spend.total_calls} calls)</p>
                  </div>
                )}
                {p.username && <p className="text-xs text-text-tertiary mt-1">{p.username}</p>}
                {p.shop_count !== undefined && <p className="text-xs text-text-tertiary mt-1">{p.shop_count} shop(s)</p>}
              </div>
            ) : (
              <div>
                {p.spend && p.spend.total_calls > 0 ? (
                  <div className="mb-2 space-y-1">
                    <p className="text-lg font-bold text-text-primary">{formatCostPrecise(p.spend.month_cost)}</p>
                    <p className="text-xs text-text-tertiary">{p.spend.month_calls} calls this month</p>
                    <p className="text-xs text-text-tertiary">All time: {formatCostPrecise(p.spend.total_cost)}</p>
                  </div>
                ) : (
                  <p className="text-xs text-text-tertiary">{p.message}</p>
                )}
                <span className="text-xs text-accent group-hover:underline mt-1 inline-block">View console →</span>
              </div>
            )}
          </a>
        ))}
      </div>
    </div>
  );
}

export default function ApiUsagePage() {
  const [summary, setSummary] = useState<UsageSummary | null>(null);
  const [period, setPeriod] = useState('month');
  const [loading, setLoading] = useState(true);
  const [historyFilter, setHistoryFilter] = useState<{ service?: string; operation?: string } | null>(null);
  const [balances, setBalances] = useState<ApiBalanceResult | null>(null);
  const [balanceRefreshing, setBalanceRefreshing] = useState(false);

  const fetchBalances = useCallback(() => {
    setBalanceRefreshing(true);
    getApiBalances().then(setBalances).catch(() => null).finally(() => setBalanceRefreshing(false));
  }, []);

  useEffect(() => {
    fetchBalances();
  }, [fetchBalances]);

  useEffect(() => {
    setLoading(true);
    getUsageSummary(period).then(setSummary).catch(() => null).finally(() => setLoading(false));
  }, [period]);

  if (loading && !summary) return <div className="flex items-center justify-center h-64 text-text-secondary">Loading...</div>;

  return (
    <div className="max-w-4xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">API Usage</h1>
          <p className="text-sm text-text-secondary mt-1">Track spending across Claude, OpenAI, and Replicate</p>
        </div>
        <div className="flex gap-1 bg-bg-secondary rounded-lg p-1 border border-border">
          {PERIODS.map((p) => (
            <button
              key={p.value}
              onClick={() => { setPeriod(p.value); setHistoryFilter(null); }}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                period === p.value ? 'bg-accent text-white' : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      <BalanceCards balances={balances} onRefresh={fetchBalances} refreshing={balanceRefreshing} />

      {summary && (
        <>
          {/* Totals */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <button
              onClick={() => setHistoryFilter({})}
              className="bg-bg-secondary border border-border rounded-xl p-4 text-left hover:border-accent/50 transition-colors"
            >
              <p className="text-xs text-text-tertiary">Total Spend</p>
              <p className="text-2xl font-bold text-text-primary mt-1">{formatCurrency(summary.total_cost)}</p>
              <p className="text-xs text-text-tertiary mt-1">Click for history</p>
            </button>
            <button
              onClick={() => setHistoryFilter({})}
              className="bg-bg-secondary border border-border rounded-xl p-4 text-left hover:border-accent/50 transition-colors"
            >
              <p className="text-xs text-text-tertiary">API Calls</p>
              <p className="text-2xl font-bold text-text-primary mt-1">{summary.total_calls.toLocaleString()}</p>
              <p className="text-xs text-text-tertiary mt-1">Click for history</p>
            </button>
            {summary.by_service.map((svc) => (
              <button
                key={svc.service}
                onClick={() => setHistoryFilter({ service: svc.service })}
                className="bg-bg-secondary border border-border rounded-xl p-4 text-left hover:border-accent/50 transition-colors"
              >
                <p className={`text-xs ${SERVICE_COLORS[svc.service] || 'text-text-tertiary'} capitalize`}>{svc.service}</p>
                <p className="text-xl font-bold text-text-primary mt-1">{formatCostPrecise(svc.total_cost)}</p>
                <p className="text-xs text-text-tertiary">{svc.calls} calls</p>
              </button>
            ))}
          </div>

          {/* Call History (when a filter is active) */}
          {historyFilter && (
            <CallHistoryPanel
              period={period}
              service={historyFilter.service}
              operation={historyFilter.operation}
              onClose={() => setHistoryFilter(null)}
            />
          )}

          {/* By Service */}
          <section className="bg-bg-secondary border border-border rounded-xl p-5">
            <h2 className="text-base font-semibold text-text-primary mb-4">Cost by Service</h2>
            <div className="space-y-3">
              {summary.by_service.map((svc) => {
                const pct = summary.total_cost > 0 ? (svc.total_cost / summary.total_cost) * 100 : 0;
                return (
                  <button
                    key={svc.service}
                    onClick={() => setHistoryFilter({ service: svc.service })}
                    className="w-full text-left hover:bg-bg-tertiary/30 rounded-lg p-1 -m-1 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className={`text-sm font-medium capitalize ${SERVICE_COLORS[svc.service] || 'text-text-primary'}`}>{svc.service}</span>
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-text-tertiary">{svc.calls} calls</span>
                        {svc.input_tokens > 0 && (
                          <span className="text-xs text-text-tertiary">{(svc.input_tokens / 1000).toFixed(1)}K in / {(svc.output_tokens / 1000).toFixed(1)}K out</span>
                        )}
                        <span className="text-sm font-semibold text-text-primary">{formatCostPrecise(svc.total_cost)}</span>
                      </div>
                    </div>
                    <div className="w-full bg-bg-tertiary rounded-full h-2">
                      <div className="bg-accent rounded-full h-2 transition-all" style={{ width: `${Math.max(2, pct)}%` }} />
                    </div>
                  </button>
                );
              })}
            </div>
          </section>

          {/* By Operation */}
          <section className="bg-bg-secondary border border-border rounded-xl p-5">
            <h2 className="text-base font-semibold text-text-primary mb-4">Cost by Operation</h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left px-3 py-2 text-xs text-text-tertiary font-medium">Service</th>
                    <th className="text-left px-3 py-2 text-xs text-text-tertiary font-medium">Operation</th>
                    <th className="text-left px-3 py-2 text-xs text-text-tertiary font-medium">Model</th>
                    <th className="text-right px-3 py-2 text-xs text-text-tertiary font-medium">Calls</th>
                    <th className="text-right px-3 py-2 text-xs text-text-tertiary font-medium">Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.by_operation.map((op, i) => (
                    <tr
                      key={i}
                      onClick={() => setHistoryFilter({ service: op.service, operation: op.operation })}
                      className="border-b border-border last:border-b-0 cursor-pointer hover:bg-bg-tertiary/50 transition-colors"
                    >
                      <td className={`px-3 py-2 text-sm capitalize ${SERVICE_COLORS[op.service] || 'text-text-primary'}`}>{op.service}</td>
                      <td className="px-3 py-2 text-sm text-text-secondary">{op.operation.replace(/_/g, ' ')}</td>
                      <td className="px-3 py-2 text-xs text-text-tertiary font-mono">{op.model || '-'}</td>
                      <td className="px-3 py-2 text-sm text-text-primary text-right">{op.calls}</td>
                      <td className="px-3 py-2 text-sm font-medium text-text-primary text-right">{formatCostPrecise(op.total_cost)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {summary.by_operation.length === 0 && (
                <p className="text-center text-text-tertiary text-sm py-8">No API calls recorded yet</p>
              )}
            </div>
          </section>

          {/* Daily Trend */}
          {summary.daily.length > 0 && (
            <section className="bg-bg-secondary border border-border rounded-xl p-5">
              <h2 className="text-base font-semibold text-text-primary mb-4">Daily Spend</h2>
              <div className="space-y-2">
                {Object.entries(
                  summary.daily.reduce<Record<string, { cost: number; calls: number; services: Record<string, number> }>>((acc, d) => {
                    const day = d.day?.split('T')[0] || 'unknown';
                    if (!acc[day]) acc[day] = { cost: 0, calls: 0, services: {} };
                    acc[day].cost += d.cost;
                    acc[day].calls += d.calls;
                    acc[day].services[d.service] = (acc[day].services[d.service] || 0) + d.cost;
                    return acc;
                  }, {})
                ).reverse().map(([day, data]) => (
                  <div key={day} className="flex items-center justify-between p-2 bg-bg-tertiary rounded-lg">
                    <span className="text-sm text-text-primary font-mono">{day}</span>
                    <div className="flex items-center gap-4">
                      {Object.entries(data.services).map(([svc, cost]) => (
                        <span key={svc} className={`text-xs ${SERVICE_COLORS[svc] || 'text-text-tertiary'}`}>
                          {svc}: {formatCostPrecise(cost)}
                        </span>
                      ))}
                      <span className="text-xs text-text-tertiary">{data.calls} calls</span>
                      <span className="text-sm font-semibold text-text-primary">{formatCostPrecise(data.cost)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}
        </>
      )}

      {summary && summary.total_calls === 0 && (
        <div className="text-center py-16 text-text-tertiary">
          <p className="text-lg">No API usage recorded yet</p>
          <p className="text-sm mt-1">Usage tracking starts with the next batch run or Drew's Mind design</p>
        </div>
      )}
    </div>
  );
}
