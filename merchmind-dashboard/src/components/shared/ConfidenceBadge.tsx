import { getConfidenceLevel } from '../../utils/formatters';

const colorMap = {
  high: 'bg-confidence-high/20 text-confidence-high',
  medium: 'bg-confidence-medium/20 text-confidence-medium',
  low: 'bg-confidence-low/20 text-confidence-low',
};

export default function ConfidenceBadge({ score }: { score: number }) {
  const level = getConfidenceLevel(score);
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${colorMap[level]}`}>
      {score}/40
    </span>
  );
}
