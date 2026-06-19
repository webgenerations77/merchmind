import React, { useEffect, useCallback } from 'react';
import {
  View,
  Text,
  Pressable,
  ScrollView,
  StyleSheet,
  RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import FastImage from 'react-native-fast-image';
import { colors, typography, spacing } from '../../theme';
import { useBatchStore } from '../../store/batchStore';
import { useAlertStore } from '../../store/alertStore';
import { useProductStore } from '../../store/productStore';
import { useReviewStore } from '../../store/reviewStore';
import { SkeletonBox } from '../../components/shared/LoadingSkeleton';
import { formatCurrency, formatTimeAgo, formatDate } from '../../utils/formatters';
import { SEVERITY_ICONS } from '../../utils/constants';
import type { HomeScreenProps } from '../../navigation/types';

export default function HomeScreen({ navigation }: HomeScreenProps) {
  const { currentBatch, fetchCurrentBatch } = useBatchStore();
  const { alerts, unreadCount, fetchAlerts, resolveAlert } = useAlertStore();
  const { products, fetchProducts } = useProductStore();
  const { queue, fetchQueue } = useReviewStore();

  const [refreshing, setRefreshing] = React.useState(false);
  const [batchBannerDismissed, setBatchBannerDismissed] = React.useState(false);

  const loadAll = useCallback(async () => {
    await Promise.all([fetchCurrentBatch(), fetchAlerts(), fetchProducts(), fetchQueue()]);
  }, [fetchCurrentBatch, fetchAlerts, fetchProducts, fetchQueue]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const onRefresh = async () => {
    setRefreshing(true);
    await loadAll();
    setRefreshing(false);
  };

  const pendingReviewCount = queue.filter(d => d.status === 'ready').length;
  const topPick = queue.find(d => d.status === 'ready');
  const showBatchBanner = pendingReviewCount > 0 && !batchBannerDismissed;

  const totalRevenue = products.reduce((sum, p) => sum + p.total_revenue, 0);
  const weeklyRevenue = totalRevenue * 0.25; // approx
  const monthlyRevenue = totalRevenue;

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.wordmark}>✦ MerchMind</Text>
        <View style={styles.headerActions}>
          <Pressable
            onPress={() => navigation.navigate('Settings')}
            hitSlop={8}
            style={styles.iconBtn}
            accessibilityRole="button"
            accessibilityLabel="Settings"
          >
            <Text style={styles.headerIcon}>⚙️</Text>
          </Pressable>
          <Pressable
            style={styles.iconBtn}
            hitSlop={8}
            accessibilityRole="button"
            accessibilityLabel={`${unreadCount} unread alerts`}
          >
            <Text style={styles.headerIcon}>🔔</Text>
            {unreadCount > 0 && (
              <View style={styles.notifBadge}>
                <Text style={styles.notifBadgeText}>{unreadCount}</Text>
              </View>
            )}
          </Pressable>
        </View>
      </View>

      <ScrollView
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.accent} />}
        contentContainerStyle={styles.scroll}
        showsVerticalScrollIndicator={false}
      >
        {showBatchBanner && (
          <Pressable
            style={styles.batchBanner}
            onPress={() => navigation.getParent()?.navigate('ReviewTab')}
            accessibilityRole="button"
            accessibilityLabel={`${pendingReviewCount} products ready for review`}
          >
            <View style={styles.batchBannerContent}>
              <Text style={styles.batchBannerTitle}>
                🎉 {pendingReviewCount} products ready for review
              </Text>
              {topPick && (
                <Text style={styles.batchBannerSub}>
                  Top pick: {topPick.concept_name} (score: {Math.round(topPick.final_score)})
                </Text>
              )}
            </View>
            <Pressable
              onPress={() => setBatchBannerDismissed(true)}
              hitSlop={8}
              accessibilityRole="button"
              accessibilityLabel="Dismiss"
            >
              <Text style={styles.dismissX}>✕</Text>
            </Pressable>
          </Pressable>
        )}

        <View style={styles.statsRow}>
          <StatCard label="Live Products" value={products.length.toString()} emoji="🛍️" />
          <StatCard label="Weekly Revenue" value={formatCurrency(weeklyRevenue)} emoji="📈" />
          <StatCard label="This Month" value={formatCurrency(monthlyRevenue)} emoji="💰" />
        </View>

        {alerts.length > 0 && (
          <Section title="Alerts" badge={alerts.length}>
            {alerts.map(alert => (
              <View key={alert.id} style={styles.alertRow}>
                <Text style={styles.alertIcon}>{SEVERITY_ICONS[alert.severity]}</Text>
                <View style={styles.alertContent}>
                  <Text style={styles.alertMessage} numberOfLines={2}>{alert.message}</Text>
                  <Text style={styles.alertTime}>{formatTimeAgo(alert.created_at)}</Text>
                </View>
                <Pressable
                  onPress={() => resolveAlert(alert.id)}
                  hitSlop={8}
                  style={styles.resolveBtn}
                  accessibilityRole="button"
                  accessibilityLabel="Resolve alert"
                >
                  <Text style={styles.resolveText}>✓</Text>
                </Pressable>
              </View>
            ))}
          </Section>
        )}

        <Section title="Recent Products">
          {products.slice(0, 5).length === 0 ? (
            <Text style={styles.emptyText}>No products yet. Approve some in your review queue.</Text>
          ) : (
            products.slice(0, 5).map(product => (
              <View key={product.id} style={styles.productRow}>
                <View style={styles.productThumb}>
                  {product.processed_image_url ? (
                    <FastImage
                      source={{ uri: product.processed_image_url }}
                      style={styles.thumbImage}
                      resizeMode={FastImage.resizeMode.cover}
                    />
                  ) : (
                    <View style={[styles.thumbImage, styles.thumbPlaceholder]} />
                  )}
                </View>
                <View style={styles.productInfo}>
                  <Text style={styles.productName} numberOfLines={1}>{product.concept_name}</Text>
                  <Text style={styles.productDate}>{formatDate(product.published_at ?? product.created_at)}</Text>
                </View>
                <Text style={styles.productRevenue}>{formatCurrency(product.total_revenue)}</Text>
              </View>
            ))
          )}
        </Section>
      </ScrollView>
    </SafeAreaView>
  );
}

function StatCard({ label, value, emoji }: { label: string; value: string; emoji: string }) {
  return (
    <View style={styles.statCard}>
      <Text style={styles.statEmoji}>{emoji}</Text>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

function Section({ title, badge, children }: { title: string; badge?: number; children: React.ReactNode }) {
  return (
    <View style={styles.section}>
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>{title}</Text>
        {badge !== undefined && badge > 0 && (
          <View style={styles.sectionBadge}>
            <Text style={styles.sectionBadgeText}>{badge}</Text>
          </View>
        )}
      </View>
      <View style={styles.sectionContent}>{children}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg.primary },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.xxl,
    paddingVertical: spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  wordmark: { fontSize: 22, fontWeight: '800', color: colors.text.primary },
  headerActions: { flexDirection: 'row', gap: spacing.md },
  iconBtn: { position: 'relative', padding: spacing.xs },
  headerIcon: { fontSize: 20 },
  notifBadge: {
    position: 'absolute',
    top: -2,
    right: -2,
    backgroundColor: '#EF4444',
    borderRadius: 8,
    width: 16,
    height: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  notifBadgeText: { color: colors.white, fontSize: 10, fontWeight: '700' },
  scroll: { padding: spacing.lg, gap: spacing.xl, paddingBottom: 40 },
  batchBanner: {
    backgroundColor: colors.accent,
    borderRadius: 16,
    padding: spacing.lg,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  batchBannerContent: { flex: 1, gap: 4 },
  batchBannerTitle: { ...typography.subheading, color: colors.white },
  batchBannerSub: { ...typography.caption, color: `${colors.white}CC` },
  dismissX: { color: `${colors.white}CC`, fontSize: 16, padding: spacing.xs },
  statsRow: { flexDirection: 'row', gap: spacing.sm },
  statCard: {
    flex: 1,
    backgroundColor: colors.bg.secondary,
    borderRadius: 12,
    padding: spacing.md,
    alignItems: 'center',
    gap: 4,
    borderWidth: 1,
    borderColor: colors.border,
  },
  statEmoji: { fontSize: 20 },
  statValue: { ...typography.subheading, color: colors.text.primary, fontSize: 15 },
  statLabel: { ...typography.caption, color: colors.text.tertiary, textAlign: 'center' },
  section: { gap: spacing.sm },
  sectionHeader: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  sectionTitle: { ...typography.subheading, color: colors.text.primary },
  sectionBadge: {
    backgroundColor: colors.confidence.low,
    borderRadius: 10,
    paddingHorizontal: 7,
    paddingVertical: 2,
  },
  sectionBadgeText: { color: colors.white, fontSize: 11, fontWeight: '700' },
  sectionContent: {
    backgroundColor: colors.bg.secondary,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
    overflow: 'hidden',
  },
  alertRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    padding: spacing.lg,
    gap: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    minHeight: 60,
  },
  alertIcon: { fontSize: 18, marginTop: 2 },
  alertContent: { flex: 1, gap: 2 },
  alertMessage: { ...typography.body, color: colors.text.primary },
  alertTime: { ...typography.caption, color: colors.text.tertiary },
  resolveBtn: {
    width: 32,
    height: 32,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  resolveText: { color: colors.confidence.high, fontSize: 14, fontWeight: '700' },
  productRow: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing.md,
    gap: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    minHeight: 64,
  },
  productThumb: {
    width: 48,
    height: 48,
    borderRadius: 8,
    overflow: 'hidden',
    backgroundColor: colors.bg.tertiary,
  },
  thumbImage: { width: 48, height: 48 },
  thumbPlaceholder: { backgroundColor: colors.bg.tertiary },
  productInfo: { flex: 1 },
  productName: { ...typography.body, color: colors.text.primary, fontWeight: '500' },
  productDate: { ...typography.caption, color: colors.text.tertiary, marginTop: 2 },
  productRevenue: { ...typography.mono, color: colors.confidence.high, fontWeight: '700' },
  emptyText: { ...typography.body, color: colors.text.tertiary, padding: spacing.lg, textAlign: 'center' },
});
