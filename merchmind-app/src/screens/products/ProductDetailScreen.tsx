import React, { useEffect, useState } from 'react';
import { View, Text, Pressable, ScrollView, StyleSheet, Alert, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import FastImage from 'react-native-fast-image';
import { colors, typography, spacing } from '../../theme';
import { getProduct } from '../../api/products';
import { getSalesByProduct } from '../../api/sales';
import { useProductStore } from '../../store/productStore';
import { RevenueChart } from '../../components/charts/RevenueChart';
import { ErrorState } from '../../components/shared/ErrorState';
import { formatCurrency, formatDate } from '../../utils/formatters';
import type { ProductDetailScreenProps } from '../../navigation/types';
import type { Product, Sale } from '../../types/api';

export default function ProductDetailScreen({ route, navigation }: ProductDetailScreenProps) {
  const { productId } = route.params;
  const [product, setProduct] = useState<Product | null>(null);
  const [sales, setSales] = useState<Sale[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { unpublishProduct } = useProductStore();

  useEffect(() => { loadData(); }, [productId]);

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [p, s] = await Promise.all([getProduct(productId), getSalesByProduct(productId)]);
      setProduct(p);
      setSales(s);
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUnpublish = () => {
    Alert.alert(
      'Unpublish Product',
      'This will immediately remove the product from your Shopify store. Are you sure?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Unpublish',
          style: 'destructive',
          onPress: async () => {
            await unpublishProduct(productId);
            navigation.goBack();
          },
        },
      ],
    );
  };

  if (isLoading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator color={colors.accent} size="large" />
        </View>
      </SafeAreaView>
    );
  }

  if (error || !product) {
    return (
      <SafeAreaView style={styles.container}>
        <ErrorState message={error ?? 'Product not found'} onRetry={loadData} />
      </SafeAreaView>
    );
  }

  const isUnderperformer = product.units_sold === 0 && product.days_live >= 28;
  const weeklySales = sales.slice(0, 8).map(s => ({
    week: s.sale_date,
    revenue: s.gross_revenue,
  }));

  const mockupUrl = product.mockup_urls
    ? Object.values(product.mockup_urls)[0]?.[0]
    : product.processed_image_url;

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.navBar}>
        <Pressable onPress={() => navigation.goBack()} hitSlop={8} style={styles.backBtn} accessibilityRole="button" accessibilityLabel="Go back">
          <Text style={styles.backText}>← Back</Text>
        </Pressable>
        <Pressable onPress={handleUnpublish} style={styles.unpublishBtn} accessibilityRole="button" accessibilityLabel="Unpublish product">
          <Text style={styles.unpublishText}>⚠️ Unpublish</Text>
        </Pressable>
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {mockupUrl && (
          <FastImage
            source={{ uri: mockupUrl }}
            style={styles.heroImage}
            resizeMode={FastImage.resizeMode.cover}
          />
        )}

        <View style={styles.infoSection}>
          <Text style={styles.productName}>{product.concept_name}</Text>
          <Text style={styles.productType}>{product.product_type.replace('_', ' ')}</Text>
          <Text style={styles.publishDate}>
            Published {formatDate(product.published_at ?? product.created_at)}
          </Text>
        </View>

        <RevenueChart data={weeklySales} title="Revenue (8 weeks)" />

        <View style={styles.statsGrid}>
          <StatItem label="Total Revenue" value={formatCurrency(product.total_revenue)} accent />
          <StatItem label="Units Sold" value={product.units_sold.toString()} />
          <StatItem label="Net Profit" value={formatCurrency(product.net_profit)} />
          <StatItem label="Days Live" value={`${product.days_live}d`} />
        </View>

        {isUnderperformer && (
          <View style={styles.underperformerSection}>
            <Text style={styles.underperformerTitle}>⚠️ No sales in 4 weeks</Text>
            <Text style={styles.underperformerText}>What would you like to do?</Text>
            <View style={styles.underperformerActions}>
              <Pressable style={styles.keepBtn} accessibilityRole="button" accessibilityLabel="Keep live">
                <Text style={styles.keepBtnText}>Keep Live</Text>
              </Pressable>
              <Pressable style={styles.saleBtn} accessibilityRole="button" accessibilityLabel="Run a sale">
                <Text style={styles.saleBtnText}>Run a Sale</Text>
              </Pressable>
              <Pressable style={styles.unpublishActionBtn} onPress={handleUnpublish} accessibilityRole="button" accessibilityLabel="Unpublish">
                <Text style={styles.unpublishActionText}>Unpublish</Text>
              </Pressable>
            </View>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function StatItem({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <View style={styles.statItem}>
      <Text style={[styles.statValue, accent && { color: colors.confidence.high }]}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg.primary },
  loadingContainer: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  navBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  backBtn: { minHeight: 44, justifyContent: 'center' },
  backText: { ...typography.body, color: colors.accent },
  unpublishBtn: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.confidence.low,
    minHeight: 36,
    justifyContent: 'center',
  },
  unpublishText: { ...typography.caption, color: colors.confidence.low, fontWeight: '600' },
  scroll: { padding: spacing.lg, gap: spacing.xl, paddingBottom: 40 },
  heroImage: {
    width: '100%',
    height: 280,
    borderRadius: 16,
    backgroundColor: colors.bg.secondary,
  },
  infoSection: { gap: spacing.xs },
  productName: { ...typography.heading, color: colors.text.primary },
  productType: { ...typography.body, color: colors.accent, textTransform: 'capitalize' },
  publishDate: { ...typography.caption, color: colors.text.tertiary },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  statItem: {
    flex: 1,
    minWidth: '45%',
    backgroundColor: colors.bg.secondary,
    borderRadius: 12,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
    gap: 4,
  },
  statValue: { ...typography.heading, color: colors.text.primary },
  statLabel: { ...typography.caption, color: colors.text.secondary },
  underperformerSection: {
    backgroundColor: `${'#EAB308'}11`,
    borderWidth: 1,
    borderColor: '#EAB308',
    borderRadius: 16,
    padding: spacing.xl,
    gap: spacing.md,
  },
  underperformerTitle: { ...typography.subheading, color: '#EAB308' },
  underperformerText: { ...typography.body, color: colors.text.secondary },
  underperformerActions: { flexDirection: 'row', gap: spacing.sm },
  keepBtn: {
    flex: 1,
    padding: spacing.md,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    minHeight: 44,
    justifyContent: 'center',
  },
  keepBtnText: { ...typography.caption, color: colors.text.secondary, fontWeight: '600' },
  saleBtn: {
    flex: 1,
    padding: spacing.md,
    borderRadius: 10,
    backgroundColor: `${colors.accent}22`,
    borderWidth: 1,
    borderColor: `${colors.accent}66`,
    alignItems: 'center',
    minHeight: 44,
    justifyContent: 'center',
  },
  saleBtnText: { ...typography.caption, color: colors.accent, fontWeight: '600' },
  unpublishActionBtn: {
    flex: 1,
    padding: spacing.md,
    borderRadius: 10,
    backgroundColor: `${colors.confidence.low}22`,
    borderWidth: 1,
    borderColor: `${colors.confidence.low}66`,
    alignItems: 'center',
    minHeight: 44,
    justifyContent: 'center',
  },
  unpublishActionText: { ...typography.caption, color: colors.confidence.low, fontWeight: '600' },
});
