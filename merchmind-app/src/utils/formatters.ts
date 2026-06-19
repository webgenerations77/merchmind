import { format, formatDistanceToNow, addDays, nextMonday } from 'date-fns';
import { HOLIDAY_LABELS } from './constants';

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(amount);
}

export function formatScore(score: number): string {
  return Math.round(score).toString();
}

export function formatTimeAgo(dateString: string): string {
  return formatDistanceToNow(new Date(dateString), { addSuffix: true });
}

export function formatDate(dateString: string): string {
  return format(new Date(dateString), 'MMM d, yyyy');
}

export function formatWeekOf(dateString: string): string {
  return format(new Date(dateString), "'Week of' MMM d");
}

export function getUpcomingMondays(count = 12): Array<{ date: Date; label: string; holiday?: string }> {
  const mondays: Array<{ date: Date; label: string; holiday?: string }> = [];
  let current = nextMonday(new Date());

  for (let i = 0; i < count; i++) {
    const monthDay = format(current, 'MM-dd');
    const holiday = HOLIDAY_LABELS[monthDay];
    mondays.push({
      date: current,
      label: format(current, 'EEE MMM d'),
      holiday,
    });
    current = addDays(current, 7);
  }

  return mondays;
}

export function getConfidenceLevel(score: number): 'high' | 'medium' | 'low' {
  if (score >= 75) return 'high';
  if (score >= 55) return 'medium';
  return 'low';
}

export function formatProductType(type: string): string {
  return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}
