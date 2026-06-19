import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '../../theme';
import type { AlertSeverity } from '../../types/api';

interface Props {
  severity: AlertSeverity;
  count?: number;
}

const SEVERITY_COLORS: Record<AlertSeverity, string> = {
  info: colors.action.regen,
  warning: '#EAB308',
  critical: '#EF4444',
};

const SEVERITY_EMOJIS: Record<AlertSeverity, string> = {
  info: 'ℹ️',
  warning: '⚠️',
  critical: '🚨',
};

export function AlertBadge({ severity, count }: Props) {
  const color = SEVERITY_COLORS[severity];
  return (
    <View style={[styles.badge, { borderColor: color }]}>
      <Text style={styles.emoji}>{SEVERITY_EMOJIS[severity]}</Text>
      {count !== undefined && (
        <Text style={[styles.count, { color }]}>{count}</Text>
      )}
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
  count: {
    ...typography.caption,
    fontWeight: '600',
  },
});
