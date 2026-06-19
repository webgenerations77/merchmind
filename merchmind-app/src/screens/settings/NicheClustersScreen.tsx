import React, { useEffect, useState } from 'react';
import { View, Text, Pressable, ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, typography, spacing } from '../../theme';
import { useSettingsStore } from '../../store/settingsStore';
import { NICHE_CLUSTERS } from '../../utils/constants';
import type { NicheClustersScreenProps } from '../../navigation/types';

export default function NicheClustersScreen({}: NicheClustersScreenProps) {
  const { settings, fetchSettings, updateSettings } = useSettingsStore();
  const [selected, setSelected] = useState<Set<string>>(new Set());

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  useEffect(() => {
    if (settings) {
      setSelected(new Set(settings.selected_cluster_ids));
    }
  }, [settings]);

  const toggle = async (id: string) => {
    const next = new Set(selected);
    if (next.has(id)) {
      if (next.size > 1) next.delete(id);
    } else {
      next.add(id);
    }
    setSelected(next);
    await updateSettings({ selected_cluster_ids: [...next] });
  };

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.subtitle}>Toggle the niches you want the pipeline to scrape and generate for.</Text>
        <View style={styles.cards}>
          {NICHE_CLUSTERS.map(niche => {
            const isSelected = selected.has(niche.id);
            return (
              <Pressable
                key={niche.id}
                style={[styles.card, isSelected && styles.cardSelected]}
                onPress={() => toggle(niche.id)}
                accessibilityRole="checkbox"
                accessibilityState={{ checked: isSelected }}
                accessibilityLabel={niche.name}
              >
                <Text style={styles.cardEmoji}>{niche.emoji}</Text>
                <Text style={styles.cardName}>{niche.name}</Text>
                <Text style={[styles.status, isSelected && styles.statusActive]}>
                  {isSelected ? '✓ Active' : 'Inactive'}
                </Text>
              </Pressable>
            );
          })}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg.primary },
  scroll: { padding: spacing.lg, gap: spacing.lg, paddingBottom: 40 },
  subtitle: { ...typography.body, color: colors.text.secondary },
  cards: { gap: spacing.sm },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    padding: spacing.lg,
    backgroundColor: colors.bg.secondary,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: colors.border,
    minHeight: 64,
  },
  cardSelected: { borderColor: colors.accent, backgroundColor: `${colors.accent}11` },
  cardEmoji: { fontSize: 24 },
  cardName: { ...typography.subheading, color: colors.text.primary, flex: 1 },
  status: { ...typography.caption, color: colors.text.tertiary },
  statusActive: { color: colors.confidence.high, fontWeight: '600' },
});
