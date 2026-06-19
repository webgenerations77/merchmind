import React, { useEffect, useState, useRef, useCallback } from 'react';
import {
  View,
  Text,
  Pressable,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import BottomSheet from '@gorhom/bottom-sheet';
import { colors, typography, spacing } from '../../theme';
import { useReviewStore } from '../../store/reviewStore';
import { getDesign } from '../../api/designs';
import { getDesignAssets } from '../../api/marketing';
import { MockupGallery } from '../../components/review/MockupGallery';
import { ScoreStrip } from '../../components/review/ScoreStrip';
import { DesignDetailsStrip } from '../../components/review/DesignDetailsStrip';
import { ListingDetails } from '../../components/review/ListingDetails';
import { PricingBreakdown } from '../../components/review/PricingBreakdown';
import { MarketingAssets } from '../../components/review/MarketingAssets';
import { ActionBar } from '../../components/review/ActionBar';
import { RegenSheet } from '../../components/review/RegenSheet';
import { DelayPicker } from '../../components/review/DelayPicker';
import { ErrorState } from '../../components/shared/ErrorState';
import { regenerateDesign } from '../../api/designs';
import { disableAsset, updateAssetContent } from '../../api/marketing';
import { haptics } from '../../utils/haptics';
import type { ReviewCardScreenProps } from '../../navigation/types';
import type { Design, MarketingAsset } from '../../types/api';

export default function ReviewCardScreen({ route, navigation }: ReviewCardScreenProps) {
  const { designId } = route.params;
  const { queue, currentIndex, sessionActions, approveDesign, rejectDesign, delayDesign, goToNext, goToPrevious } = useReviewStore();
  const [design, setDesign] = useState<Design | null>(null);
  const [assets, setAssets] = useState<MarketingAsset[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editedTitle, setEditedTitle] = useState('');
  const [editedTags, setEditedTags] = useState<string[]>([]);
  const [editedDesc, setEditedDesc] = useState('');
  const regenRef = useRef<BottomSheet>(null);
  const delayRef = useRef<BottomSheet>(null);

  useEffect(() => {
    loadDesign();
  }, [designId]);

  const loadDesign = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [d, a] = await Promise.all([getDesign(designId), getDesignAssets(designId)]);
      setDesign(d);
      setAssets(a);
      setEditedTitle(d.listing_title);
      setEditedTags(d.listing_tags);
      setEditedDesc(d.seo_description);
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  const currentQueueIndex = queue.findIndex(d => d.id === designId);
  const totalCount = queue.filter(d => !sessionActions[d.id]).length + Object.keys(sessionActions).length;

  const navigate = (dir: 'next' | 'prev') => {
    const pending = queue.filter(d => !sessionActions[d.id]);
    const curr = pending.findIndex(d => d.id === designId);
    if (dir === 'next' && curr < pending.length - 1) {
      navigation.replace('ReviewCard', { designId: pending[curr + 1].id, index: curr + 1 });
    } else if (dir === 'prev' && curr > 0) {
      navigation.replace('ReviewCard', { designId: pending[curr - 1].id, index: curr - 1 });
    }
  };

  const pending = queue.filter(d => !sessionActions[d.id]);
  const positionInPending = pending.findIndex(d => d.id === designId) + 1;

  const handleApprove = async () => {
    await approveDesign(designId);
    const nextPending = queue.filter(d => !sessionActions[d.id] && d.id !== designId);
    if (nextPending.length === 0) {
      navigation.replace('BatchComplete');
    } else {
      navigation.replace('ReviewCard', { designId: nextPending[0].id, index: 0 });
    }
  };

  const handleReject = async () => {
    await rejectDesign(designId);
    const nextPending = queue.filter(d => !sessionActions[d.id] && d.id !== designId);
    if (nextPending.length === 0) {
      navigation.replace('BatchComplete');
    } else {
      navigation.replace('ReviewCard', { designId: nextPending[0].id, index: 0 });
    }
  };

  const handleDelay = () => {
    delayRef.current?.expand();
  };

  const handleDelaySelect = async (week: string) => {
    await delayDesign(designId, week);
    const nextPending = queue.filter(d => !sessionActions[d.id] && d.id !== designId);
    if (nextPending.length === 0) {
      navigation.replace('BatchComplete');
    } else {
      navigation.replace('ReviewCard', { designId: nextPending[0].id, index: 0 });
    }
  };

  const handleRegen = async (prompt: string) => {
    if (!design) return;
    await regenerateDesign(design.id, prompt);
    regenRef.current?.close();
    await loadDesign();
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

  if (error || !design) {
    return (
      <SafeAreaView style={styles.container}>
        <ErrorState message={error ?? 'Design not found'} onRetry={loadDesign} />
      </SafeAreaView>
    );
  }

  const pricingData = Object.keys(design.mockup_urls ?? {}).map(type => ({
    productType: type,
    baseCost: 12.5,
    markup: 2.5,
    trendBoost: design.trend_score * 0.03,
    retail: 12.5 * 2.5 + design.trend_score * 0.03,
    floorPrice: 24.99,
  }));

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.navBar}>
        <Pressable
          onPress={() => navigation.goBack()}
          hitSlop={8}
          style={styles.navBtn}
          accessibilityRole="button"
          accessibilityLabel="Go back"
        >
          <Text style={styles.navBtnText}>←</Text>
        </Pressable>
        <Text style={styles.navCounter}>{positionInPending} of {pending.length}</Text>
        <View style={styles.navArrows}>
          <Pressable
            onPress={() => navigate('prev')}
            disabled={positionInPending <= 1}
            hitSlop={8}
            style={[styles.navArrowBtn, positionInPending <= 1 && styles.navArrowDisabled]}
            accessibilityRole="button"
            accessibilityLabel="Previous design"
          >
            <Text style={styles.navBtnText}>‹</Text>
          </Pressable>
          <Pressable
            onPress={() => navigate('next')}
            disabled={positionInPending >= pending.length}
            hitSlop={8}
            style={[styles.navArrowBtn, positionInPending >= pending.length && styles.navArrowDisabled]}
            accessibilityRole="button"
            accessibilityLabel="Next design"
          >
            <Text style={styles.navBtnText}>›</Text>
          </Pressable>
        </View>
      </View>

      <ScrollView showsVerticalScrollIndicator={false} style={styles.scroll}>
        <ScoreStrip
          score={design.final_score}
          version={design.version}
          nicheCluster={design.niche_cluster}
          source={design.source}
          reasoning={design.claude_reasoning}
        />

        <MockupGallery mockupUrls={design.mockup_urls ?? {}} />

        <DesignDetailsStrip
          fontPair={design.font_pair}
          styleLabel={design.style_label}
          designColors={design.colors}
          productTypes={Object.keys(design.mockup_urls ?? {})}
        />

        <ListingDetails
          title={editedTitle}
          tags={editedTags}
          seoDescription={editedDesc}
          onTitleChange={setEditedTitle}
          onTagsChange={setEditedTags}
          onDescriptionChange={setEditedDesc}
        />

        <PricingBreakdown
          pricingData={pricingData}
          onPriceOverride={() => {}}
        />

        <MarketingAssets
          assets={assets}
          onDisable={(assetId) => disableAsset(assetId)}
          onEdit={(assetId, updates) => updateAssetContent(assetId, updates)}
        />

        <View style={{ height: 100 }} />
      </ScrollView>

      <ActionBar
        onApprove={handleApprove}
        onReject={handleReject}
        onDelay={handleDelay}
        onRegen={() => regenRef.current?.expand()}
      />

      <RegenSheet
        bottomSheetRef={regenRef}
        currentPrompt={design.image_prompt}
        onRegenerate={handleRegen}
      />

      <DelayPicker
        bottomSheetRef={delayRef}
        onSelect={handleDelaySelect}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg.primary },
  loadingContainer: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  navBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    minHeight: 52,
  },
  navBtn: {
    padding: spacing.sm,
    minWidth: 44,
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  navBtnText: { color: colors.text.primary, fontSize: 22 },
  navCounter: { ...typography.subheading, color: colors.text.secondary },
  navArrows: { flexDirection: 'row', gap: spacing.xs },
  navArrowBtn: {
    padding: spacing.sm,
    minWidth: 44,
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  navArrowDisabled: { opacity: 0.3 },
  scroll: { flex: 1 },
});
