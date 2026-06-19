import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { colors, typography, spacing } from '../../theme';
import { haptics } from '../../utils/haptics';

interface Props {
  onApprove: () => void;
  onReject: () => void;
  onDelay: () => void;
  onRegen: () => void;
  isLoading?: boolean;
}

export function ActionBar({ onApprove, onReject, onDelay, onRegen, isLoading }: Props) {
  const insets = useSafeAreaInsets();

  const actions = [
    {
      label: '❌ Reject',
      onPress: () => { haptics.reject(); onReject(); },
      style: styles.rejectBtn,
      textStyle: styles.rejectText,
      accessibilityLabel: 'Reject design',
    },
    {
      label: '📅 Delay',
      onPress: () => { haptics.delay(); onDelay(); },
      style: styles.delayBtn,
      textStyle: styles.delayText,
      accessibilityLabel: 'Delay design',
    },
    {
      label: '🔁 Regen',
      onPress: () => { haptics.regen(); onRegen(); },
      style: styles.regenBtn,
      textStyle: styles.regenText,
      accessibilityLabel: 'Regenerate design',
    },
    {
      label: '✅ Approve',
      onPress: () => { haptics.approve(); onApprove(); },
      style: styles.approveBtn,
      textStyle: styles.approveText,
      accessibilityLabel: 'Approve design',
    },
  ];

  return (
    <View style={[styles.container, { paddingBottom: insets.bottom + spacing.md }]}>
      {actions.map(action => (
        <Pressable
          key={action.label}
          style={({ pressed }) => [action.style, pressed && styles.pressed, isLoading && styles.disabled]}
          onPress={action.onPress}
          disabled={isLoading}
          accessibilityRole="button"
          accessibilityLabel={action.accessibilityLabel}
        >
          <Text style={action.textStyle}>{action.label}</Text>
        </Pressable>
      ))}
    </View>
  );
}

const btnBase: object = {
  flex: 1,
  minHeight: 52,
  alignItems: 'center',
  justifyContent: 'center',
  borderRadius: 10,
  paddingVertical: spacing.md,
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    gap: spacing.sm,
    padding: spacing.md,
    backgroundColor: colors.bg.secondary,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  rejectBtn: {
    ...btnBase,
    backgroundColor: colors.bg.tertiary,
  },
  delayBtn: {
    ...btnBase,
    backgroundColor: `${colors.action.delay}22`,
    borderWidth: 1,
    borderColor: `${colors.action.delay}66`,
  },
  regenBtn: {
    ...btnBase,
    backgroundColor: `${colors.action.regen}22`,
    borderWidth: 1,
    borderColor: `${colors.action.regen}66`,
  },
  approveBtn: {
    ...btnBase,
    backgroundColor: colors.action.approve,
  },
  rejectText: {
    ...typography.caption,
    color: colors.text.secondary,
    fontWeight: '600',
    fontSize: 12,
  },
  delayText: {
    ...typography.caption,
    color: colors.action.delay,
    fontWeight: '600',
    fontSize: 12,
  },
  regenText: {
    ...typography.caption,
    color: colors.action.regen,
    fontWeight: '600',
    fontSize: 12,
  },
  approveText: {
    ...typography.caption,
    color: colors.white,
    fontWeight: '700',
    fontSize: 12,
  },
  pressed: { opacity: 0.7 },
  disabled: { opacity: 0.4 },
});
