import React, { useEffect, useState } from 'react';
import { View, Text, Pressable, StyleSheet, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { FlashList } from '@shopify/flash-list';
import FastImage from 'react-native-fast-image';
import { colors, typography, spacing } from '../../theme';
import { useProductStore } from '../../store/productStore';
import { EmptyState } from '../../components/shared/EmptyState';
import { formatCurrency } from '../../utils/formatters';

export default function PublishQueueScreen() {
  const { products, fetchProducts, isLoading } = useProductStore();
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => { fetchProducts(); }, [fetchProducts]);

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchProducts();
    setRefreshing(false);
  };

  const queued = products.filter(p => p.publish_status === 'queued');

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Publish Queue</Text>
        <Text style={styles.subtitle}>Publishing at 9:00am · {queued.length} products</Text>
      </View>

      {queued.length === 0 ? (
        <EmptyState
          title="No products queued"
          subtitle="Approve some products in your review queue."
          emoji="📤"
        />
      ) : (
        <FlashList
          data={queued}
          estimatedItemSize={80}
          keyExtractor={item => item.id}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.accent} />}
          renderItem={({ item, index }) => (
            <View style={styles.row}>
              <Text style={styles.dragHandle}>⠿</Text>
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
                <Text style={styles.rowTypes}>{item.product_type.replace('_', ' ')}</Text>
              </View>
              <Text style={[styles.statusText, item.publish_status === 'published' && styles.publishedText]}>
                {item.publish_status === 'published' ? '✅ Live' : `#${index + 1}`}
              </Text>
            </View>
          )}
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
  },
  title: { ...typography.heading, color: colors.text.primary },
  subtitle: { ...typography.caption, color: colors.text.secondary, marginTop: 4 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing.lg,
    gap: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    minHeight: 72,
    backgroundColor: colors.bg.primary,
  },
  dragHandle: { color: colors.text.tertiary, fontSize: 20, width: 24, textAlign: 'center' },
  thumb: {
    width: 52,
    height: 52,
    borderRadius: 8,
    overflow: 'hidden',
    backgroundColor: colors.bg.secondary,
  },
  thumbImg: { width: 52, height: 52 },
  thumbPlaceholder: { backgroundColor: colors.bg.tertiary },
  rowInfo: { flex: 1 },
  rowName: { ...typography.body, color: colors.text.primary, fontWeight: '500' },
  rowTypes: { ...typography.caption, color: colors.text.secondary, marginTop: 2 },
  statusText: { ...typography.mono, color: colors.text.tertiary, fontSize: 13 },
  publishedText: { color: colors.confidence.high },
});
