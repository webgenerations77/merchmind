import { useEffect, useState } from 'react';
import { getUsageSummary, type UsageSummary } from '../api/apiUsage';
import { formatCurrency } from '../utils/formatters';

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

export default function ApiUsagePage() {
  const [summary, setSummary] = useState<UsageSummary | null>(null);
  const [period, setPeriod] = useState('month');
  const [loading, setLoading] = useState(true);

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
              onClick={() => setPeriod(p.value)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                period === p.value ? 'bg-accent text-white' : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {summary && (
        <>
          {/* Totals */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-bg-secondary border border-border rounded-xl p-4">
              <p className="text-xs text-text-tertiary">Total Spend</p>
              <p className="text-2xl font-bold text-text-primary mt-1">{formatCurrency(summary.total_cost)}</p>
            </div>
            <div className="bg-bg-secondary border border-border rounded-xl p-4">
              <p className="text-xs text-text-tertiary">API Calls</p>
              <p className="text-2xl font-bold text-text-primary mt-1">{summary.total_calls.toLocaleString()}</p>
            </div>
            {summary.by_service.map((svc) => (
              <div key={svc.service} className="bg-bg-secondary border border-border rounded-xl p-4">
                <p className={`text-xs ${SERVICE_COLORS[svc.service] || 'text-text-tertiary'} capitalize`}>{svc.service}</p>
                <p className="text-xl font-bold text-text-primary mt-1">{formatCurrency(svc.total_cost)}</p>
                <p className="text-xs text-text-tertiary">{svc.calls} calls</p>
              </div>
            ))}
          </div>

          {/* By Service */}
          <section className="bg-bg-secondary border border-border rounded-xl p-5">
            <h2 className="text-base font-semibold text-text-primary mb-4">Cost by Service</h2>
            <div className="space-y-3">
              {summary.by_service.map((svc) => {
                const pct = summary.total_cost > 0 ? (svc.total_cost / summary.total_cost) * 100 : 0;
                return (
                  <div key={svc.service}>
                    <div className="flex items-center justify-between mb-1">
                      <span className={`text-sm font-medium capitalize ${SERVICE_COLORS[svc.service] || 'text-text-primary'}`}>{svc.service}</span>
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-text-tertiary">{svc.calls} calls</span>
                        {svc.input_tokens > 0 && (
                          <span className="text-xs text-text-tertiary">{(svc.input_tokens / 1000).toFixed(1)}K in / {(svc.output_tokens / 1000).toFixed(1)}K out</span>
                        )}
                        <span className="text-sm font-semibold text-text-primary">{formatCurrency(svc.total_cost)}</span>
                      </div>
                    </div>
                    <div className="w-full bg-bg-tertiary rounded-full h-2">
                      <div className="bg-accent rounded-full h-2 transition-all" style={{ width: `${Math.max(2, pct)}%` }} />
                    </div>
                  </div>
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
                    <tr key={i} className="border-b border-border last:border-b-0">
                      <td className={`px-3 py-2 text-sm capitalize ${SERVICE_COLORS[op.service] || 'text-text-primary'}`}>{op.service}</td>
                      <td className="px-3 py-2 text-sm text-text-secondary">{op.operation.replace(/_/g, ' ')}</td>
                      <td className="px-3 py-2 text-xs text-text-tertiary font-mono">{op.model || '-'}</td>
                      <td className="px-3 py-2 text-sm text-text-primary text-right">{op.calls}</td>
                      <td className="px-3 py-2 text-sm font-medium text-text-primary text-right">{formatCurrency(op.total_cost)}</td>
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
                          {svc}: {formatCurrency(cost)}
                        </span>
                      ))}
                      <span className="text-xs text-text-tertiary">{data.calls} calls</span>
                      <span className="text-sm font-semibold text-text-primary">{formatCurrency(data.cost)}</span>
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
