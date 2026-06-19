import React, { useState, useEffect } from 'react';
import { View, Text, Pressable, ScrollView, StyleSheet, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Animated, { useSharedValue, withSpring, useAnimatedStyle } from 'react-native-reanimated';
import { colors, typography, spacing } from '../../theme';
import { useSSE } from '../../hooks/useSSE';
import { BATCH_STEPS } from '../../utils/constants';
import { storage } from '../../navigation/RootNavigator';
import type { OnboardingBatchProgressProps } from '../../navigation/types';

type StepStatus = 'pending' | 'running' | 'completed' | 'failed';

interface Step {
  name: string;
  status: StepStatus;
}

const STEP_ICONS: Record<StepStatus, string> = {
  pending: '⏳',
  running: '🔄',
  completed: '✅',
  failed: '❌',
};

export default function BatchProgressScreen({ route, navigation }: OnboardingBatchProgressProps) {
  const { batchId } = route.params;
  const [steps, setSteps] = useState<Step[]>(
    BATCH_STEPS.map(name => ({ name, status: 'pending' })),
  );
  const [allDone, setAllDone] = useState(false);

  useSSE<{ step: string; status: StepStatus }>(
    `/batches/${batchId}/progress`,
    (data) => {
      setSteps(prev =>
        prev.map(s =>
          s.name.toLowerCase().includes(data.step.toLowerCase())
            ? { ...s, status: data.status }
            : s,
        ),
      );
      if (data.status === 'completed' && data.step === BATCH_STEPS[BATCH_STEPS.length - 1]) {
        setAllDone(true);
      }
    },
  );

  // Simulate progress in mock mode
  useEffect(() => {
    let idx = 0;
    const interval = setInterval(() => {
      if (idx >= BATCH_STEPS.length) {
        setAllDone(true);
        clearInterval(interval);
        return;
      }
      const currentIdx = idx;
      setSteps(prev =>
        prev.map((s, i) => {
          if (i === currentIdx) return { ...s, status: 'running' };
          if (i < currentIdx) return { ...s, status: 'completed' };
          return s;
        }),
      );
      idx++;
    }, 2200);
    return () => clearInterval(interval);
  }, []);

  const handleDone = () => {
    storage.set('onboarding_complete', true);
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.title}>Running your first batch</Text>
        <Text style={styles.subtitle}>Usually takes 15–25 minutes</Text>

        <View style={styles.steps}>
          {steps.map((step, i) => (
            <View key={i} style={styles.stepRow}>
              <Text style={styles.stepIcon}>
                {step.status === 'running' ? (
                  '🔄'
                ) : (
                  STEP_ICONS[step.status]
                )}
              </Text>
              <Text style={[
                styles.stepName,
                step.status === 'completed' && styles.stepDone,
                step.status === 'running' && styles.stepRunning,
              ]}>
                {step.name}
              </Text>
            </View>
          ))}
        </View>

        <View style={styles.closedNote}>
          <Text style={styles.closedNoteText}>
            You can close the app — we'll notify you when ready
          </Text>
        </View>

        <Pressable
          style={[styles.doneBtn, !allDone && styles.doneBtnSecondary]}
          onPress={handleDone}
          accessibilityRole="button"
          accessibilityLabel="Go to dashboard"
        >
          <Text style={[styles.doneBtnText, !allDone && styles.doneBtnTextSecondary]}>
            {allDone ? '🎉 View my products →' : 'Go to dashboard →'}
          </Text>
        </Pressable>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg.primary },
  scroll: { padding: spacing.xxl, gap: spacing.xl, paddingBottom: 40 },
  title: { ...typography.heading, color: colors.text.primary },
  subtitle: { ...typography.body, color: colors.text.secondary },
  steps: {
    backgroundColor: colors.bg.secondary,
    borderRadius: 16,
    padding: spacing.xl,
    gap: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
  },
  stepRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    minHeight: 36,
  },
  stepIcon: { fontSize: 18, width: 24, textAlign: 'center' },
  stepName: { ...typography.body, color: colors.text.tertiary, flex: 1 },
  stepDone: { color: colors.confidence.high },
  stepRunning: { color: colors.text.primary, fontWeight: '600' },
  closedNote: {
    backgroundColor: colors.bg.tertiary,
    borderRadius: 10,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
  },
  closedNoteText: { ...typography.caption, color: colors.text.secondary, textAlign: 'center', lineHeight: 18 },
  doneBtn: {
    backgroundColor: colors.accent,
    paddingVertical: spacing.lg,
    borderRadius: 14,
    alignItems: 'center',
    minHeight: 56,
    justifyContent: 'center',
  },
  doneBtnSecondary: {
    backgroundColor: colors.bg.secondary,
    borderWidth: 1,
    borderColor: colors.border,
  },
  doneBtnText: { ...typography.subheading, color: colors.white, fontSize: 17 },
  doneBtnTextSecondary: { color: colors.text.secondary },
});
