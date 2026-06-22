import React, { useEffect, useState } from 'react';
import { View, Text, ScrollView, TextInput, Pressable, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, typography, spacing } from '../../theme';
import { useSettingsStore } from '../../store/settingsStore';
import { formatCurrency } from '../../utils/formatters';
import type { PricingRulesScreenProps } from '../../navigation/types';
import type { FloorPrices } from '../../types/api';

const PRODUCT_TYPE_LABELS: Array<{ key: keyof FloorPrices; label: string }> = [
  { key: 't_shirt', label: 'T-Shirt' },
  { key: 'mug', label: 'Mug' },
  { key: 'hat', label: 'Hat' },
  { key: 'sticker', label: 'Sticker' },
  { key: 'phone_case', label: 'Phone Case' },
];

export default function PricingRulesScreen({}: PricingRulesScreenProps) {
  const { settings, fetchSettings, updateSettings } = useSettingsStore();
  const [editing, setEditing] = useState<string | null>(null);
  const [editVal, setEditVal] = useState('');

  useEffect(() => { fetchSettings(); }, [fetchSettings]);

  const commitEdit = async (key: keyof FloorPrices) => {
    const parsed = parseFloat(editVal);
    if (!isNaN(parsed) && parsed > 0 && settings) {
      const newFloors = { ...settings.floor_prices, [key]: parsed };
      await updateSettings({ floor_prices: newFloors });
    }
    setEditing(null);
  };

  if (!settings) return null;

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.section}>
          <View style={styles.row}>
            <Text style={styles.rowLabel}>Base markup</Text>
            <Text style={styles.rowValue}>{settings.base_markup}× cost</Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.rowLabel}>Max trend boost</Text>
            <Text style={styles.rowValue}>+{(settings.trend_boost_max * 100).toFixed(0)}%</Text>
          </View>
        </View>

        <Text style={styles.sectionTitle}>Floor prices</Text>
        <View style={styles.section}>
          {PRODUCT_TYPE_LABELS.map(({ key, label }) => (
            <View key={key} style={styles.row}>
              <Text style={styles.rowLabel}>{label}</Text>
              {editing === key ? (
                <TextInput
                  value={editVal}
                  onChangeText={setEditVal}
                  onBlur={() => commitEdit(key)}
                  keyboardType="decimal-pad"
                  style={styles.input}
                  autoFocus
                  accessibilityLabel={`${label} floor price`}
                />
              ) : (
                <Pressable
                  onPress={() => {
                    setEditing(key);
                    setEditVal(settings.floor_prices[key].toFixed(2));
                  }}
                  hitSlop={8}
                  accessibilityRole="button"
                >
                  <Text style={styles.rowValue}>{formatCurrency(settings.floor_prices[key])} ✏️</Text>
                </Pressable>
              )}
            </View>
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg.primary },
  scroll: { padding: spacing.lg, gap: spacing.lg, paddingBottom: 40 },
  sectionTitle: {
    ...typography.caption,
    color: colors.text.tertiary,
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginTop: spacing.md,
  },
  section: {
    backgroundColor: colors.bg.secondary,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
    overflow: 'hidden',
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    minHeight: 52,
  },
  rowLabel: { ...typography.body, color: colors.text.primary },
  rowValue: { ...typography.mono, color: colors.text.secondary },
  input: {
    ...typography.mono,
    color: colors.text.primary,
    borderBottomWidth: 1,
    borderBottomColor: colors.accent,
    minWidth: 80,
    textAlign: 'right',
    padding: 4,
  },
});
