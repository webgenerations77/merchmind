import React, { useEffect } from 'react';
import { View, Text, ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, typography, spacing } from '../../theme';
import { useSettingsStore } from '../../store/settingsStore';
import type { ScheduleSettingsScreenProps } from '../../navigation/types';

const TIMELINE = [
  { emoji: '🔄', label: 'Batch runs', key: 'batch_schedule_cron', display: 'Sunday 10:00pm' },
  { emoji: '📱', label: 'Review notification', key: 'review_notification_time', display: 'Monday 7:00am' },
  { emoji: '🚀', label: 'Products go live', key: 'publish_time', display: 'Monday 9:00am' },
];

export default function ScheduleSettingsScreen({}: ScheduleSettingsScreenProps) {
  const { settings, fetchSettings } = useSettingsStore();

  useEffect(() => { fetchSettings(); }, [fetchSettings]);

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.subtitle}>
          Your automated pipeline runs on this schedule every week.
        </Text>

        <View style={styles.section}>
          {TIMELINE.map((item, i) => (
            <View key={i} style={styles.row}>
              <Text style={styles.emoji}>{item.emoji}</Text>
              <View style={styles.rowInfo}>
                <Text style={styles.rowLabel}>{item.label}</Text>
                <Text style={styles.rowTime}>{item.display}</Text>
              </View>
            </View>
          ))}
        </View>

        <View style={styles.infoBox}>
          <Text style={styles.infoText}>
            ℹ️ Custom scheduling is coming in a future update. For now, the pipeline runs every Sunday at 10pm UTC with Monday morning review.
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg.primary },
  scroll: { padding: spacing.lg, gap: spacing.xl, paddingBottom: 40 },
  subtitle: { ...typography.body, color: colors.text.secondary },
  section: {
    backgroundColor: colors.bg.secondary,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
    overflow: 'hidden',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing.lg,
    gap: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    minHeight: 64,
  },
  emoji: { fontSize: 24 },
  rowInfo: { flex: 1 },
  rowLabel: { ...typography.body, color: colors.text.secondary },
  rowTime: { ...typography.subheading, color: colors.text.primary, marginTop: 2 },
  infoBox: {
    padding: spacing.lg,
    backgroundColor: `${colors.accent}11`,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: `${colors.accent}33`,
  },
  infoText: { ...typography.body, color: colors.text.secondary, lineHeight: 22 },
});
