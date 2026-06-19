import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '../../theme';
import { getConfidenceLevel, formatScore } from '../../utils/formatters';

interface Props {
  score: number;
  size?: 'sm' | 'md';
}

export function ConfidenceBadge({ score, size = 'md' }: Props) {
  const level = getConfidenceLevel(score);
  const color = colors.confidence[level];
  const emoji = level === 'high' ? '🟢' : level === 'medium' ? '🟡' : '🔴';
  const isSmall = size === 'sm';

  return (
    <View style={[styles.badge, { borderColor: color, paddingHorizontal: isSmall ? spacing.xs : spacing.sm }]}>
      <Text style={[styles.emoji, isSmall && styles.emojiSm]}>{emoji}</Text>
      <Text style={[styles.score, { color }, isSmall && styles.scoreSm]}>
        {formatScore(score)}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingVertical: spacing.xs,
    paddingHorizontal: spacing.sm,
    borderRadius: 6,
    borderWidth: 1,
    backgroundColor: colors.bg.tertiary,
  },
  emoji: { fontSize: 12 },
  emojiSm: { fontSize: 10 },
  score: {
    ...typography.mono,
    fontSize: 14,
    fontWeight: '700',
  },
  scoreSm: { fontSize: 12 },
});
