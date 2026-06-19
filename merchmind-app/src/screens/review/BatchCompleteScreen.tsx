import React, { useEffect } from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
  withDelay,
} from 'react-native-reanimated';
import { colors, typography, spacing } from '../../theme';
import { useReviewStore } from '../../store/reviewStore';
import type { BatchCompleteScreenProps } from '../../navigation/types';

export default function BatchCompleteScreen({ navigation }: BatchCompleteScreenProps) {
  const { sessionActions } = useReviewStore();

  const scale = useSharedValue(0);
  const opacity = useSharedValue(0);

  useEffect(() => {
    scale.value = withDelay(100, withSpring(1, { damping: 12, stiffness: 150 }));
    opacity.value = withDelay(200, withSpring(1));
  }, []);

  const animStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
    opacity: opacity.value,
  }));

  const approved = Object.values(sessionActions).filter(a => a === 'approved').length;
  const rejected = Object.values(sessionActions).filter(a => a === 'rejected').length;
  const delayed = Object.values(sessionActions).filter(a => a === 'delayed').length;

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <Animated.View style={[styles.checkmark, animStyle]}>
          <Text style={styles.checkmarkEmoji}>✅</Text>
        </Animated.View>

        <Text style={styles.title}>Review complete!</Text>

        <View style={styles.summary}>
          <SummaryRow emoji="✅" label="Approved" count={approved} color={colors.confidence.high} />
          <SummaryRow emoji="❌" label="Rejected" count={rejected} color={colors.text.secondary} />
          <SummaryRow emoji="📅" label="Delayed" count={delayed} color={colors.action.delay} />
        </View>

        <View style={styles.publishInfo}>
          <Text style={styles.publishText}>Products will go live at 9:00am today</Text>
          <Pressable
            onPress={() => navigation.getParent()?.navigate('QueueTab')}
            hitSlop={8}
            accessibilityRole="button"
          >
            <Text style={styles.publishLink}>Edit publish queue →</Text>
          </Pressable>
        </View>

        <Pressable
          style={styles.doneBtn}
          onPress={() => {
            navigation.getParent()?.navigate('HomeTab');
          }}
          accessibilityRole="button"
          accessibilityLabel="Confirm and go home"
        >
          <Text style={styles.doneBtnText}>Confirm & Done</Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

function SummaryRow({ emoji, label, count, color }: { emoji: string; label: string; count: number; color: string }) {
  return (
    <View style={styles.summaryRow}>
      <Text style={styles.summaryEmoji}>{emoji}</Text>
      <Text style={styles.summaryLabel}>{label}</Text>
      <Text style={[styles.summaryCount, { color }]}>{count}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg.primary },
  content: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.xxl,
    gap: spacing.xxl,
  },
  checkmark: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: `${colors.confidence.high}22`,
    alignItems: 'center',
    justifyContent: 'center',
  },
  checkmarkEmoji: { fontSize: 52 },
  title: { ...typography.display, color: colors.text.primary, textAlign: 'center' },
  summary: {
    width: '100%',
    backgroundColor: colors.bg.secondary,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: colors.border,
    overflow: 'hidden',
  },
  summaryRow: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing.lg,
    gap: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    minHeight: 52,
  },
  summaryEmoji: { fontSize: 20, width: 28 },
  summaryLabel: { ...typography.body, color: colors.text.secondary, flex: 1 },
  summaryCount: { ...typography.subheading, fontWeight: '700' },
  publishInfo: {
    alignItems: 'center',
    gap: spacing.sm,
    padding: spacing.lg,
    backgroundColor: colors.bg.secondary,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
    width: '100%',
  },
  publishText: { ...typography.body, color: colors.text.primary },
  publishLink: { ...typography.caption, color: colors.accent },
  doneBtn: {
    width: '100%',
    backgroundColor: colors.accent,
    paddingVertical: spacing.lg,
    borderRadius: 14,
    alignItems: 'center',
    minHeight: 56,
    justifyContent: 'center',
  },
  doneBtnText: { ...typography.subheading, color: colors.white, fontSize: 18 },
});
