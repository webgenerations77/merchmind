import React, { useState } from 'react';
import { View, Text, Pressable, ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, typography, spacing } from '../../theme';
import { NICHE_CLUSTERS } from '../../utils/constants';
import { storage } from '../../navigation/RootNavigator';
import type { OnboardingPickNichesProps } from '../../navigation/types';

export default function PickNichesScreen({ navigation }: OnboardingPickNichesProps) {
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const toggle = (id: string) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const handleContinue = () => {
    storage.set('selected_clusters', JSON.stringify([...selected]));
    navigation.navigate('Pricing');
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.title}>What will you sell?</Text>
        <Text style={styles.subtitle}>Pick at least 1. You can add more later.</Text>

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
                <View style={styles.cardHeader}>
                  <Text style={styles.cardEmoji}>{niche.emoji}</Text>
                  <Text style={styles.cardName}>{niche.name}</Text>
                  {isSelected && <Text style={styles.checkmark}>✓</Text>}
                </View>
                <View style={styles.keywords}>
                  {niche.keywords.map(kw => (
                    <View key={kw} style={styles.kwChip}>
                      <Text style={styles.kwText}>{kw}</Text>
                    </View>
                  ))}
                </View>
              </Pressable>
            );
          })}
        </View>

        <Pressable
          style={[styles.continueBtn, selected.size === 0 && styles.disabled]}
          onPress={handleContinue}
          disabled={selected.size === 0}
          accessibilityRole="button"
          accessibilityLabel="Continue"
        >
          <Text style={styles.continueBtnText}>Continue ({selected.size} selected) →</Text>
        </Pressable>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg.primary },
  scroll: { padding: spacing.xxl, gap: spacing.lg, paddingBottom: 40 },
  title: { ...typography.heading, color: colors.text.primary },
  subtitle: { ...typography.body, color: colors.text.secondary },
  cards: { gap: spacing.md },
  card: {
    padding: spacing.lg,
    backgroundColor: colors.bg.secondary,
    borderRadius: 16,
    borderWidth: 2,
    borderColor: colors.border,
    gap: spacing.md,
  },
  cardSelected: {
    borderColor: colors.accent,
    backgroundColor: `${colors.accent}11`,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  cardEmoji: { fontSize: 28 },
  cardName: { ...typography.subheading, color: colors.text.primary, flex: 1 },
  checkmark: { fontSize: 18, color: colors.accent, fontWeight: '700' },
  keywords: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.xs },
  kwChip: {
    paddingHorizontal: spacing.sm,
    paddingVertical: 3,
    borderRadius: 10,
    backgroundColor: colors.bg.tertiary,
  },
  kwText: { ...typography.caption, color: colors.text.tertiary },
  continueBtn: {
    backgroundColor: colors.accent,
    paddingVertical: spacing.lg,
    borderRadius: 14,
    alignItems: 'center',
    minHeight: 56,
    justifyContent: 'center',
    marginTop: spacing.md,
  },
  disabled: { opacity: 0.4 },
  continueBtnText: { ...typography.subheading, color: colors.white, fontSize: 17 },
});
