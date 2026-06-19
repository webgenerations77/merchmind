import React from 'react';
import { View, Text, ScrollView, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '../../theme';
import type { DesignColors } from '../../types/api';

interface Props {
  fontPair: string;
  styleLabel: string;
  designColors: DesignColors;
  productTypes: string[];
}

export function DesignDetailsStrip({ fontPair, styleLabel, designColors, productTypes }: Props) {
  const colorValues = Object.values(designColors);

  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      style={styles.container}
      contentContainerStyle={styles.content}
    >
      <Chip label={`🔤 ${fontPair}`} />
      <Chip label={`🎨 ${styleLabel}`} />
      <View style={styles.colorChip}>
        <Text style={styles.chipLabel}>Colors</Text>
        <View style={styles.swatches}>
          {colorValues.map((c, i) => (
            <View key={i} style={[styles.swatch, { backgroundColor: c }]} />
          ))}
        </View>
      </View>
      <Chip label={`📦 ${productTypes.map(t => t.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())).join(' · ')}`} />
    </ScrollView>
  );
}

function Chip({ label }: { label: string }) {
  return (
    <View style={styles.chip}>
      <Text style={styles.chipLabel} numberOfLines={1}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  content: {
    padding: spacing.md,
    gap: spacing.sm,
    flexDirection: 'row',
    alignItems: 'center',
  },
  chip: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.bg.tertiary,
    minHeight: 32,
    justifyContent: 'center',
  },
  chipLabel: {
    ...typography.caption,
    color: colors.text.secondary,
  },
  colorChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.bg.tertiary,
    minHeight: 32,
  },
  swatches: {
    flexDirection: 'row',
    gap: 4,
  },
  swatch: {
    width: 14,
    height: 14,
    borderRadius: 7,
    borderWidth: 1,
    borderColor: colors.border,
  },
});
