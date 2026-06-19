import React, { useEffect, useState } from 'react';
import { View, Text, Pressable, StyleSheet, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { FlashList } from '@shopify/flash-list';
import FastImage from 'react-native-fast-image';
import { colors, typography, spacing } from '../../theme';
import { useProductStore } from '../../store/productStore';
import { EmptyState } from '../../components/shared/EmptyState';
import { ErrorState } from '../../components/shared/ErrorState';
import { ConfidenceBadge } from '../../components/shared/ConfidenceBadge';
import { formatCurrency } from '../../utils/formatters';
import type { LiveProductsScreenProps } from '../../navigation/types';

type SortKey = 'revenue' | 'trend_score' | 'date';

export default function LiveProductsScreen({ navigation }: LiveProductsScreenProps) {
  const { products, fetchProducts, isLoading, error, setSortKey, sortKey } = useProductStore();
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => { fetchProducts(); }, [fetchProducts]);

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchProducts();
    setRefreshing(false);
  };

  const sorted = [...products].sort((a, b) => {
    if (sortKey === 'revenue') return b.total_revenue - a.total_revenue;
    if (sortKey === 'trend_score') return (b.trend_score ?? 0) - (a.trend_score ?? 0);
    return new Date(b.published_at ?? b.created_at).getTime() - new Date(a.published_at ?? a.created_at).getTime();
  });

  if (error && products.length === 0) {
    return (
      <SafeAreaView style={styles.container}>
        <ErrorState message={error} onRetry={fetchProducts} />
      </SafeAreaView>
    );
  }

  const SORT_OPTIONS: { key: SortKey; label: string }[] = [
    { key: 'revenue', label: 'Revenue' },
    { key: 'trend_score', label: 'Trend Score' },
    { key: 'date', label: 'Date' },
  ];

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Live Products</Text>
        <View style={styles.sortRow}>
          {SORT_OPTIONS.map(opt => (
            <Pressable
              key={opt.key}
              style={[styles.sortBtn, sortKey === opt.key && styles.sortBtnActive]}
              onPress={() => setSortKey(opt.key)}
              accessibilityRole="button"
              accessibilityState={{ selected: sortKey === opt.key }}
            >
              <Text style={[styles.sortBtnText, sortKey === opt.key && styles.sortBtnTextActive]}>
                {opt.label}
              </Text>
            </Pressable>
          ))}
        </View>
      </View>

      {products.length === 0 ? (
        <EmptyState
          title="No live products yet"
          subtitle="Approve products in your review queue and they'll appear here."
          emoji="🛍️"
        />
      ) : (
        <FlashList
          data={sorted}
          estimatedItemSize={80}
          keyExtractor={item => item.id}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.accent} />}
          renderItem={({ item }) => {
            const isUnderperformer = item.units_sold === 0 && item.days_live >= 28;
            return (
              <Pressable
                style={styles.row}
                onPress={() => navigation.navigate('ProductDetail', { productId: item.id })}
                accessibilityRole="button"
                accessibilityLabel={item.concept_name ?? 'Product'}
              >
                <View style={styles.thumb}>
                  {item.processed_image_url ? (
                    <FastImage
                      source={{ uri: item.processed_image_url }}
                      style={styles.thumbImg}
                      resizeMode={FastImage.resizeMode.cover}
                    />
                  ) : (
                    <View style={[styles.thumbImg, styles.thumbPlaceholder]} />
                  )}
                </View>
                <View style={styles.rowInfo}>
                  <Text style={styles.rowName} numberOfLines={1}>{item.concept_name}</Text>
                  <Text style={styles.rowType}>{item.product_type.replace('_', ' ')}</Text>
                  <Text style={styles.rowDays}>{item.days_live}d live</Text>
                </View>
                <View style={styles.rowRight}>
                  <Text style={styles.revenue}>{formatCurrency(item.total_revenue)}</Text>
                  {item.trend_score && <ConfidenceBadge score={item.trend_score} size="sm" />}
                  {isUnderperformer && <Text style={styles.alertBadge}>⚠️</Text>}
                </View>
              </Pressable>
            );
          }}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg.primary },
  header: {
    padding: spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    gap: spacing.md,
  },
  title: { ...typography.heading, color: colors.text.primary },
  sortRow: { flexDirection: 'row', gap: spacing.xs },
  sortBtn: {
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.border,
    minHeight: 32,
    justifyContent: 'center',
  },
  sortBtnActive: { borderColor: colors.accent, backgroundColor: `${colors.accent}22` },
  sortBtnText: { ...typography.caption, color: colors.text.secondary },
  sortBtnTextActive: { color: colors.accent },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing.lg,
    gap: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    minHeight: 76,
  },
  thumb: {
    width: 56,
    height: 56,
    borderRadius: 8,
    overflow: 'hidden',
    backgroundColor: colors.bg.secondary,
  },
  thumbImg: { width: 56, height: 56 },
  thumbPlaceholder: { backgroundColor: colors.bg.tertiary },
  rowInfo: { flex: 1, gap: 2 },
  rowName: { ...typography.body, color: colors.text.primary, fontWeight: '500' },
  rowType: { ...typography.caption, color: colors.text.secondary },
  rowDays: { ...typography.caption, color: colors.text.tertiary },
  rowRight: { alignItems: 'flex-end', gap: spacing.xs },
  revenue: { ...typography.mono, color: colors.confidence.high, fontWeight: '700' },
  alertBadge: { fontSize: 14 },
});
