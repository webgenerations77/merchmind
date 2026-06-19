import { formatStatus } from '../../utils/formatters';

const colorMap: Record<string, string> = {
  ready: 'bg-accent/20 text-accent',
  approved: 'bg-approve/20 text-approve',
  rejected: 'bg-reject/20 text-reject',
  delayed: 'bg-delay/20 text-delay',
  generating: 'bg-confidence-medium/20 text-confidence-medium',
  pending: 'bg-text-tertiary/20 text-text-tertiary',
  published: 'bg-approve/20 text-approve',
  live: 'bg-approve/20 text-approve',
  failed: 'bg-confidence-low/20 text-confidence-low',
  complete: 'bg-approve/20 text-approve',
  running: 'bg-regen/20 text-regen',
};

export default function StatusBadge({ status }: { status: string }) {
  const color = colorMap[status] || 'bg-text-tertiary/20 text-text-tertiary';
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${color}`}>
      {formatStatus(status)}
    </span>
  );
}
