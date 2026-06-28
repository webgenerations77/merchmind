import React, { useEffect, useCallback, useState } from 'react';
import {
  View,
  Text,
  Pressable,
  StyleSheet,
  RefreshControl,
} from 'react-native';
import { FlashList } from '@shopify/flash-list';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, typography, spacing } from '../../theme';
import { useReviewStore } from '../../store/reviewStore';
import { ReviewCard } from '../../components/review/ReviewCard';
import { EmptyState } from '../../components/shared/EmptyState';
import { ErrorState } from '../../components/shared/ErrorState';
import { ReviewCardSkeleton } from '../../components/shared/LoadingSkeleton';
import { DelayPicker } from '../../components/review/DelayPicker';
import BottomSheet from '@gorhom/bottom-sheet';
import { format } from 'date-fns';
import type { ReviewQueueScreenProps } from '../../navigation/types';
import type { DesignQueueItem } from '../../types/api';
import { haptics } from '../../utils/haptics';

type SortKey = 'score' | 'date' | 'niche';

export default function ReviewQueueScreen({ navigation }: ReviewQueueScreenProps) {
  const { queue, sessionActions, isLoading, error, fetchQueue, approveDesign, rejectDesign, delayDesign, goToIndex } = useReviewStore();
  const [sortKey, setSortKey] = useState<SortKey>('score');
  const [refreshing, setRefreshing] = useState(false);
  const [selectedDesignId, setSelectedDesignId] = useState<string | null>(null);
  const delayRef = React.useRef<BottomSheet>(null);

  useEffect(() => { fetchQueue(); }, [fetchQueue]);

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchQueue();
    setRefreshing(false);
  };

  const pending = queue.filter(d => !sessionActions[d.id]);
  const acted = queue.filter(d => sessionActions[d.id]);

  const sorted = [...pending].sort((a, b) => {
    if (sortKey === 'score') return b.final_score - a.final_score;
    if (sortKey === 'niche') return (a.niche_cluster ?? '').localeCompare(b.niche_cluster ?? '');
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });

  const handleCardPress = (design: DesignQueueItem) => {
    const index = queue.indexOf(design);
    goToIndex(index);
    navigation.navigate('ReviewCard', { designId: design.id, index });
  };

  const handleDelay = (designId: string) => {
    setSelectedDesignId(designId);
    delayRef.current?.expand();
  };

  const weekOf = format(new Date(), "'Week of' MMM d");

  if (isLoading && queue.length === 0) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.title}>{weekOf}</Text>
        </View>
        <View style={styles.skeletonGrid}>
          {[0,1,2,3,4,5].map(i => <ReviewCardSkeleton key={i} />)}
        </View>
      </SafeAreaView>
    );
  }

  if (error && queue.length === 0) {
    return (
      <SafeAreaView style={styles.container}>
        <ErrorState message={error} onRetry={fetchQueue} />
      </SafeAreaView>
    );
  }

  const SORT_OPTIONS: { key: SortKey; label: string }[] = [
    { key: 'score', label: 'Score' },
    { key: 'date', label: 'Date' },
    { key: 'niche', label: 'Niche' },
  ];

  const totalCount = queue.length;
  const reviewedCount = acted.length;
  const progressPct = totalCount > 0 ? Math.round((reviewedCount / totalCount) * 100) : 0;

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>{weekOf}</Text>
          <Text style={styles.subtitle}>{pending.length} products</Text>
        </View>
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

      {/* Feature #7: Review progress bar */}
      {totalCount > 0 && (
        <View style={styles.progressContainer}>
          <Text style={styles.progressLabel}>
            {reviewedCount} of {totalCount} reviewed · {progressPct}%
          </Text>
          <View style={styles.progressTrack}>
            <View style={[styles.progressFill, { width: `${progressPct}%` }]} />
          </View>
        </View>
      )}

      {pending.length === 0 ? (
        <EmptyState
          title="All caught up!"
          subtitle="Come back next Monday."
          emoji="🎉"
        />
      ) : (
        <FlashList
          data={sorted}
          numColumns={2}
          estimatedItemSize={260}
          keyExtractor={item => item.id}
          contentContainerStyle={styles.grid}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.accent} />}
          renderItem={({ item, index }) => (
            <ReviewCard
              design={item}
              onPress={() => handleCardPress(item)}
              onApprove={() => { haptics.approve(); approveDesign(item.id); }}
              onReject={() => { haptics.reject(); rejectDesign(item.id); }}
              onDelay={() => handleDelay(item.id)}
            />
          )}
          ListFooterComponent={acted.length > 0 ? (
            <View style={styles.approvedSection}>
              <Text style={styles.approvedLabel}>✅ {acted.length} actioned this session</Text>
            </View>
          ) : null}
        />
      )}

      <DelayPicker
        bottomSheetRef={delayRef}
        onSelect={(week) => {
          if (selectedDesignId) {
            delayDesign(selectedDesignId, week);
            setSelectedDesignId(null);
          }
        }}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg.primary },
  header: {
    padding: spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  title: { ...typography.heading, color: colors.text.primary },
  subtitle: { ...typography.caption, color: colors.text.secondary, marginTop: 2 },
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
  grid: { padding: spacing.lg },
  skeletonGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    padding: spacing.lg,
    gap: spacing.sm,
  },
  approvedSection: {
    padding: spacing.lg,
    alignItems: 'center',
    borderTopWidth: 1,
    borderTopColor: colors.border,
    marginTop: spacing.lg,
  },
  approvedLabel: { ...typography.body, color: colors.confidence.high },
  progressContainer: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  progressLabel: {
    ...typography.caption,
    color: colors.text.secondary,
    marginBottom: 6,
  },
  progressTrack: {
    width: '100%',
    height: 4,
    backgroundColor: colors.bg.tertiary,
    borderRadius: 2,
    overflow: 'hidden',
  },
  progressFill: {
    height: 4,
    backgroundColor: colors.accent,
    borderRadius: 2,
  },
});
