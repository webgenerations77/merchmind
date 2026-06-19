import React, { useEffect, useState } from 'react';
import { View, Text, Pressable, ScrollView, StyleSheet, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, typography, spacing } from '../../theme';
import { getSalesAnalytics } from '../../api/sales';
import { RevenueChart } from '../../components/charts/RevenueChart';
import { PipelinePerformanceChart } from '../../components/charts/PipelinePerformanceChart';
import { TrendCorrelationChart } from '../../components/charts/TrendCorrelationChart';
import { ErrorState } from '../../components/shared/ErrorState';
import { formatCurrency } from '../../utils/formatters';
import type { SalesAnalytics } from '../../types/api';

type DateRange = '7D' | '30D' | '90D' | 'All';

export default function AnalyticsScreen() {
  const [analytics, setAnalytics] = useState<SalesAnalytics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState<DateRange>('30D');

  const load = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getSalesAnalytics();
      setAnalytics(data);
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (isLoading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator color={colors.accent} size="large" />
        </View>
      </SafeAreaView>
    );
  }

  if (error || !analytics) {
    return (
      <SafeAreaView style={styles.container}>
        <ErrorState message={error ?? 'No data'} onRetry={load} />
      </SafeAreaView>
    );
  }

  const mockPipelineData = [
    { week: '1', generated: 20, approved: 14, published: 12 },
    { week: '2', generated: 18, approved: 12, published: 11 },
    { week: '3', generated: 22, approved: 16, published: 14 },
    { week: '4', generated: 15, approved: 10, published: 9 },
  ];

  const mockCorrelation = [
    { trendScore: 91, revenue: 476, conceptName: 'Golden Retriever Energy' },
    { trendScore: 79, revenue: 198, conceptName: 'Nurse Life' },
    { trendScore: 62, revenue: 0, conceptName: 'Leg Day Survivor' },
  ];

  const DATE_RANGES: DateRange[] = ['7D', '30D', '90D', 'All'];

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Analytics</Text>
        <View style={styles.dateRangeRow}>
          {DATE_RANGES.map(range => (
            <Pressable
              key={range}
              style={[styles.rangeBtn, dateRange === range && styles.rangeBtnActive]}
              onPress={() => setDateRange(range)}
              accessibilityRole="button"
              accessibilityState={{ selected: dateRange === range }}
            >
              <Text style={[styles.rangeBtnText, dateRange === range && styles.rangeBtnTextActive]}>
                {range}
              </Text>
            </Pressable>
          ))}
        </View>
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <View style={styles.overviewRow}>
          <OverviewCard label="Total Revenue" value={formatCurrency(analytics.total_revenue)} />
          <OverviewCard label="Units Sold" value={analytics.total_units.toString()} />
          <OverviewCard label="Net Profit" value={formatCurrency(analytics.total_profit)} />
        </View>

        <RevenueChart data={analytics.weekly_series} title="Revenue Over Time" />

        <PipelinePerformanceChart data={mockPipelineData} />

        <TrendCorrelationChart data={mockCorrelation} />

        <View style={styles.tableSection}>
          <Text style={styles.tableTitle}>Niche Performance</Text>
          <View style={styles.table}>
            <View style={styles.tableHeader}>
              <Text style={styles.th}>Niche</Text>
              <Text style={styles.th}>Revenue</Text>
              <Text style={styles.th}>Units</Text>
            </View>
            {Object.entries(analytics.revenue_by_niche).map(([niche, revenue]) => (
              <View key={niche} style={styles.tableRow}>
                <Text style={styles.td}>{niche}</Text>
                <Text style={[styles.td, styles.tdMono]}>{formatCurrency(revenue)}</Text>
                <Text style={[styles.td, styles.tdMono]}>
                  {Math.round(revenue / 34)}
                </Text>
              </View>
            ))}
          </View>
        </View>

        <View style={styles.tableSection}>
          <Text style={styles.tableTitle}>Marketing Attribution</Text>
          <View style={styles.table}>
            {Object.entries(analytics.revenue_by_channel).map(([channel, revenue]) => (
              <View key={channel} style={styles.tableRow}>
                <Text style={styles.td}>{channel.charAt(0).toUpperCase() + channel.slice(1)}</Text>
                <Text style={[styles.td, styles.tdMono]}>{formatCurrency(revenue)}</Text>
                <Text style={[styles.td, styles.tdMono]}>
                  {Math.round((revenue / analytics.total_revenue) * 100)}%
                </Text>
              </View>
            ))}
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

function OverviewCard({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.overviewCard}>
      <Text style={styles.overviewValue}>{value}</Text>
      <Text style={styles.overviewLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg.primary },
  loadingContainer: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  header: {
    padding: spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    gap: spacing.md,
  },
  title: { ...typography.heading, color: colors.text.primary },
  dateRangeRow: { flexDirection: 'row', gap: spacing.xs },
  rangeBtn: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.border,
    minHeight: 32,
    justifyContent: 'center',
  },
  rangeBtnActive: { borderColor: colors.accent, backgroundColor: `${colors.accent}22` },
  rangeBtnText: { ...typography.caption, color: colors.text.secondary },
  rangeBtnTextActive: { color: colors.accent },
  scroll: { padding: spacing.lg, gap: spacing.xl, paddingBottom: 40 },
  overviewRow: { flexDirection: 'row', gap: spacing.sm },
  overviewCard: {
    flex: 1,
    backgroundColor: colors.bg.secondary,
    borderRadius: 12,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    gap: 4,
  },
  overviewValue: { ...typography.subheading, color: colors.text.primary, fontSize: 14 },
  overviewLabel: { ...typography.caption, color: colors.text.tertiary, textAlign: 'center' },
  tableSection: { gap: spacing.sm },
  tableTitle: { ...typography.subheading, color: colors.text.primary },
  table: {
    backgroundColor: colors.bg.secondary,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
    overflow: 'hidden',
  },
  tableHeader: {
    flexDirection: 'row',
    padding: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    backgroundColor: colors.bg.tertiary,
  },
  th: { ...typography.caption, color: colors.text.tertiary, flex: 1, fontWeight: '600', textTransform: 'uppercase' },
  tableRow: {
    flexDirection: 'row',
    padding: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    minHeight: 44,
    alignItems: 'center',
  },
  td: { ...typography.body, color: colors.text.secondary, flex: 1 },
  tdMono: { ...typography.mono, fontSize: 13, color: colors.text.primary },
});
