import React, { useState } from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '../../theme';

interface Props {
  label: string;
  content: string;
}

export function InfoCollapsible({ label, content }: Props) {
  const [expanded, setExpanded] = useState(false);

  return (
    <View style={styles.container}>
      <Pressable
        onPress={() => setExpanded(v => !v)}
        style={styles.header}
        accessibilityRole="button"
        accessibilityLabel={label}
        accessibilityState={{ expanded }}
      >
        <Text style={styles.icon}>ⓘ</Text>
        <Text style={styles.label}>{label}</Text>
        <Text style={styles.chevron}>{expanded ? '▲' : '▼'}</Text>
      </Pressable>
      {expanded && (
        <View style={styles.body}>
          <Text style={styles.content}>{content}</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.border,
    overflow: 'hidden',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing.md,
    gap: spacing.sm,
    minHeight: 44,
  },
  icon: {
    color: colors.text.tertiary,
    fontSize: 14,
  },
  label: {
    ...typography.caption,
    color: colors.text.secondary,
    flex: 1,
  },
  chevron: {
    color: colors.text.tertiary,
    fontSize: 10,
  },
  body: {
    padding: spacing.md,
    paddingTop: 0,
    backgroundColor: colors.bg.tertiary,
  },
  content: {
    ...typography.caption,
    color: colors.text.secondary,
    lineHeight: 18,
  },
});
