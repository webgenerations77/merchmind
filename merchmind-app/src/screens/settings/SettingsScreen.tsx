import React, { useEffect, useState } from 'react';
import { View, Text, Pressable, ScrollView, Switch, StyleSheet, Alert, TextInput } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, typography, spacing } from '../../theme';
import { useSettingsStore } from '../../store/settingsStore';
import { ErrorState } from '../../components/shared/ErrorState';
import type { SettingsScreenProps } from '../../navigation/types';

function SliderRow({ label, value, min, max, onCommit }: {
  label: string; value: number; min: number; max: number; onCommit: (v: number) => void;
}) {
  const [localVal, setLocalVal] = useState(value);
  return (
    <View style={styles.sliderRow}>
      <View style={styles.sliderHeader}>
        <Text style={styles.sliderLabel}>{label}</Text>
        <Text style={styles.sliderValue}>{localVal}</Text>
      </View>
      <View style={styles.stepperRow}>
        <Pressable
          style={styles.stepBtn}
          onPress={() => { const v = Math.max(min, localVal - 1); setLocalVal(v); onCommit(v); }}
          accessibilityRole="button" accessibilityLabel="Decrease"
        >
          <Text style={styles.stepBtnText}>−</Text>
        </Pressable>
        <View style={styles.stepperTrack}>
          <View style={[styles.stepperFill, { width: `${((localVal - min) / (max - min)) * 100}%` }]} />
        </View>
        <Pressable
          style={styles.stepBtn}
          onPress={() => { const v = Math.min(max, localVal + 1); setLocalVal(v); onCommit(v); }}
          accessibilityRole="button" accessibilityLabel="Increase"
        >
          <Text style={styles.stepBtnText}>+</Text>
        </Pressable>
      </View>
    </View>
  );
}

export default function SettingsScreen({ navigation }: SettingsScreenProps) {
  const { settings, fetchSettings, updateSettings, isLoading, error } = useSettingsStore();

  useEffect(() => { fetchSettings(); }, [fetchSettings]);

  if (error && !settings) {
    return (
      <SafeAreaView style={styles.container}>
        <ErrorState message={error} onRetry={fetchSettings} />
      </SafeAreaView>
    );
  }

  const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      <View style={styles.sectionContent}>{children}</View>
    </View>
  );

  const NavRow = ({ label, onPress }: { label: string; onPress: () => void }) => (
    <Pressable style={styles.navRow} onPress={onPress} accessibilityRole="button" accessibilityLabel={label}>
      <Text style={styles.navRowLabel}>{label}</Text>
      <Text style={styles.navRowChevron}>›</Text>
    </Pressable>
  );

  const ToggleRow = ({ label, value, onToggle }: { label: string; value: boolean; onToggle: (v: boolean) => void }) => (
    <View style={styles.toggleRow}>
      <Text style={styles.toggleLabel}>{label}</Text>
      <Switch
        value={value}
        onValueChange={onToggle}
        trackColor={{ false: colors.border, true: colors.accent }}
        thumbColor={colors.white}
        accessibilityLabel={label}
      />
    </View>
  );

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Section title="Integrations">
          <NavRow label="API Keys" onPress={() => navigation.navigate('ApiKeys')} />
        </Section>

        <Section title="Pipeline">
          <NavRow label="Pricing Rules" onPress={() => navigation.navigate('PricingRules')} />
          <NavRow label="Niche Clusters" onPress={() => navigation.navigate('NicheClusters')} />
          <NavRow label="Schedule" onPress={() => navigation.navigate('ScheduleSettings')} />
        </Section>

        {settings && (
          <Section title="Quality">
            <SliderRow
              label="Quality threshold"
              value={settings.quality_threshold}
              min={20} max={40}
              onCommit={(v) => updateSettings({ quality_threshold: v })}
            />
            <SliderRow
              label="Score filter"
              value={settings.score_filter}
              min={25} max={50}
              onCommit={(v) => updateSettings({ score_filter: v })}
            />
            <SliderRow
              label="Max products per batch"
              value={settings.max_products_per_batch}
              min={10} max={25}
              onCommit={(v) => updateSettings({ max_products_per_batch: v })}
            />
          </Section>
        )}

        {settings && (
          <Section title="Notifications">
            <ToggleRow
              label="Batch ready"
              value={settings.notify_batch_ready}
              onToggle={(v) => updateSettings({ notify_batch_ready: v })}
            />
            <ToggleRow
              label="Underperformer alerts"
              value={settings.notify_underperformer}
              onToggle={(v) => updateSettings({ notify_underperformer: v })}
            />
            <ToggleRow
              label="Publish failures"
              value={settings.notify_publish_failed}
              onToggle={(v) => updateSettings({ notify_publish_failed: v })}
            />
          </Section>
        )}

        <Section title="Danger Zone">
          <Pressable
            style={styles.dangerRow}
            onPress={() => Alert.alert('Clear feedback history', 'This will delete all your past review decisions. Continue?', [
              { text: 'Cancel', style: 'cancel' },
              { text: 'Clear', style: 'destructive', onPress: () => {} },
            ])}
            accessibilityRole="button"
            accessibilityLabel="Clear feedback history"
          >
            <Text style={styles.dangerText}>Clear feedback history</Text>
          </Pressable>
          <Pressable
            style={styles.dangerRow}
            onPress={() => Alert.alert('Reset pricing', 'This will reset all pricing to defaults. Continue?', [
              { text: 'Cancel', style: 'cancel' },
              { text: 'Reset', style: 'destructive', onPress: () => {} },
            ])}
            accessibilityRole="button"
            accessibilityLabel="Reset pricing to defaults"
          >
            <Text style={styles.dangerText}>Reset pricing to defaults</Text>
          </Pressable>
        </Section>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg.primary },
  scroll: { padding: spacing.lg, gap: spacing.xl, paddingBottom: 40 },
  section: { gap: spacing.sm },
  sectionTitle: {
    ...typography.caption,
    color: colors.text.tertiary,
    textTransform: 'uppercase',
    letterSpacing: 1,
    paddingHorizontal: spacing.xs,
  },
  sectionContent: {
    backgroundColor: colors.bg.secondary,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
    overflow: 'hidden',
  },
  navRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    minHeight: 52,
  },
  navRowLabel: { ...typography.body, color: colors.text.primary },
  navRowChevron: { color: colors.text.tertiary, fontSize: 20 },
  toggleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    minHeight: 52,
  },
  toggleLabel: { ...typography.body, color: colors.text.primary },
  sliderRow: {
    padding: spacing.lg,
    gap: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  sliderHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  sliderLabel: { ...typography.body, color: colors.text.primary },
  sliderValue: { ...typography.mono, color: colors.accent },
  dangerRow: {
    padding: spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    minHeight: 52,
    justifyContent: 'center',
  },
  dangerText: { ...typography.body, color: colors.confidence.low },
  sliderRow: {
    padding: spacing.lg,
    gap: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  sliderHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  sliderLabel: { ...typography.body, color: colors.text.primary },
  sliderValue: { ...typography.mono, color: colors.accent },
  stepperRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  stepBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepBtnText: { ...typography.subheading, color: colors.text.primary },
  stepperTrack: {
    flex: 1,
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.border,
    overflow: 'hidden',
  },
  stepperFill: {
    height: '100%',
    backgroundColor: colors.accent,
    borderRadius: 2,
  },
});
