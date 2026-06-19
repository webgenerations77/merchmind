import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '../../theme';
import { ConfidenceBadge } from '../shared/ConfidenceBadge';

interface Props {
  score: number;
  version: number;
  nicheCluster?: string;
  source?: string;
  reasoning?: string;
}

export function ScoreStrip({ score, version, nicheCluster, source, reasoning }: Props) {
  return (
    <View style={styles.container}>
      <View style={styles.topRow}>
        <ConfidenceBadge score={score} />
        <View style={styles.meta}>
          {nicheCluster && <Text style={styles.niche}>{nicheCluster}</Text>}
          {source && <Text style={styles.source}>· {source}</Text>}
        </View>
        {version > 1 && (
          <View style={styles.versionBadge}>
            <Text style={styles.versionText}>v{version}</Text>
          </View>
        )}
      </View>
      {reasoning && (
        <Text style={styles.reasoning} numberOfLines={2}>
          "{reasoning}"
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: spacing.lg,
    gap: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  topRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    flexWrap: 'wrap',
  },
  meta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    flex: 1,
  },
  niche: {
    ...typography.caption,
    color: colors.accent,
    fontWeight: '600',
  },
  source: {
    ...typography.caption,
    color: colors.text.tertiary,
  },
  versionBadge: {
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: 4,
    backgroundColor: colors.action.regen + '33',
    borderWidth: 1,
    borderColor: colors.action.regen,
  },
  versionText: {
    ...typography.caption,
    color: colors.action.regen,
    fontWeight: '600',
  },
  reasoning: {
    ...typography.body,
    color: colors.text.secondary,
    fontStyle: 'italic',
  },
});
