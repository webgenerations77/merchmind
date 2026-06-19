import React from 'react';
import { View, Text, Pressable, StyleSheet, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, typography, spacing } from '../../theme';
import { triggerBatch } from '../../api/batches';
import type { OnboardingScheduleProps } from '../../navigation/types';

const TIMELINE = [
  { emoji: '🔄', time: 'Sunday 10pm', desc: 'Batch runs automatically' },
  { emoji: '📱', time: 'Monday 7am', desc: 'Review notification sent' },
  { emoji: '🚀', time: 'Monday 9am', desc: 'Approved products go live' },
];

export default function ScheduleScreen({ navigation }: OnboardingScheduleProps) {
  const [isTriggeringBatch, setIsTriggeringBatch] = React.useState(false);

  const handleRunNow = async () => {
    setIsTriggeringBatch(true);
    try {
      const result = await triggerBatch();
      navigation.navigate('BatchProgress', { batchId: result.task_id });
    } catch {
      navigation.navigate('BatchProgress', { batchId: 'mock-batch-id' });
    } finally {
      setIsTriggeringBatch(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.title}>Your weekly schedule</Text>

        <View style={styles.timeline}>
          {TIMELINE.map((item, i) => (
            <View key={i} style={styles.timelineRow}>
              <Text style={styles.timelineEmoji}>{item.emoji}</Text>
              <View style={styles.timelineInfo}>
                <Text style={styles.timelineTime}>{item.time}</Text>
                <Text style={styles.timelineDesc}>{item.desc}</Text>
              </View>
              {i < TIMELINE.length - 1 && <View style={styles.connector} />}
            </View>
          ))}
        </View>

        <Pressable style={styles.changeLinkRow} hitSlop={8} accessibilityRole="button">
          <Text style={styles.changeLink}>Change schedule →</Text>
        </Pressable>

        <View style={styles.divider} />

        <Text style={styles.readyTitle}>Ready to see it work?</Text>

        <Pressable
          style={[styles.runNowBtn, isTriggeringBatch && styles.disabled]}
          onPress={handleRunNow}
          disabled={isTriggeringBatch}
          accessibilityRole="button"
          accessibilityLabel="Run first batch now"
        >
          {isTriggeringBatch ? (
            <ActivityIndicator color={colors.white} />
          ) : (
            <Text style={styles.runNowText}>Run first batch now</Text>
          )}
        </Pressable>

        <Pressable
          style={styles.waitBtn}
          onPress={() => {
            const { storage } = require('../../navigation/RootNavigator');
            storage.set('onboarding_complete', true);
          }}
          accessibilityRole="button"
          accessibilityLabel="Wait until Sunday"
        >
          <Text style={styles.waitText}>Wait until Sunday</Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg.primary },
  content: { flex: 1, padding: spacing.xxl, gap: spacing.xl },
  title: { ...typography.heading, color: colors.text.primary },
  timeline: {
    backgroundColor: colors.bg.secondary,
    borderRadius: 16,
    padding: spacing.xl,
    gap: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
  },
  timelineRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.md,
    minHeight: 44,
  },
  timelineEmoji: { fontSize: 24, marginTop: 2 },
  timelineInfo: { flex: 1 },
  timelineTime: { ...typography.subheading, color: colors.text.primary },
  timelineDesc: { ...typography.body, color: colors.text.secondary, marginTop: 2 },
  connector: {
    position: 'absolute',
    left: 13,
    bottom: -spacing.lg,
    width: 2,
    height: spacing.lg,
    backgroundColor: colors.border,
  },
  changeLinkRow: { alignItems: 'flex-start' },
  changeLink: { ...typography.caption, color: colors.accent },
  divider: { height: 1, backgroundColor: colors.border },
  readyTitle: { ...typography.subheading, color: colors.text.primary, textAlign: 'center' },
  runNowBtn: {
    backgroundColor: colors.accent,
    paddingVertical: spacing.lg,
    borderRadius: 14,
    alignItems: 'center',
    minHeight: 56,
    justifyContent: 'center',
  },
  runNowText: { ...typography.subheading, color: colors.white, fontSize: 17 },
  waitBtn: {
    alignItems: 'center',
    paddingVertical: spacing.md,
    minHeight: 44,
    justifyContent: 'center',
  },
  waitText: { ...typography.body, color: colors.text.secondary },
  disabled: { opacity: 0.5 },
});
