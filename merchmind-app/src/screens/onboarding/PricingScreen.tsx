import React, { useState } from 'react';
import { View, Text, Pressable, ScrollView, TextInput, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, typography, spacing } from '../../theme';
import { formatCurrency } from '../../utils/formatters';
import type { OnboardingPricingProps } from '../../navigation/types';

const DEFAULT_FLOORS: Record<string, number> = {
  'T-Shirt': 24.99,
  'Mug': 18.99,
  'Hat': 26.99,
  'Sticker': 6.99,
  'Phone Case': 22.99,
};

export default function PricingScreen({ navigation }: OnboardingPricingProps) {
  const [floors, setFloors] = useState(DEFAULT_FLOORS);
  const [editing, setEditing] = useState<string | null>(null);
  const [editVal, setEditVal] = useState('');

  const startEdit = (type: string) => {
    setEditing(type);
    setEditVal(floors[type].toFixed(2));
  };

  const commitEdit = (type: string) => {
    const parsed = parseFloat(editVal);
    if (!isNaN(parsed) && parsed > 0) setFloors(prev => ({ ...prev, [type]: parsed }));
    setEditing(null);
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.title}>Pricing defaults</Text>
        <Text style={styles.subtitle}>You can change these anytime in Settings</Text>

        <View style={styles.section}>
          <View style={styles.row}>
            <Text style={styles.rowLabel}>Base markup</Text>
            <Text style={styles.rowValue}>2.5× cost</Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.rowLabel}>Trend boost</Text>
            <Text style={styles.rowValue}>Up to +20%</Text>
          </View>
        </View>

        <Text style={styles.sectionTitle}>Floor prices</Text>
        <Text style={styles.sectionSubtitle}>
          Ensures you never sell below cost + margin
        </Text>

        <View style={styles.section}>
          {Object.entries(floors).map(([type, price]) => (
            <View key={type} style={styles.row}>
              <Text style={styles.rowLabel}>{type}</Text>
              {editing === type ? (
                <TextInput
                  value={editVal}
                  onChangeText={setEditVal}
                  onBlur={() => commitEdit(type)}
                  keyboardType="decimal-pad"
                  style={styles.priceInput}
                  autoFocus
                  accessibilityLabel={`${type} floor price`}
                />
              ) : (
                <Pressable onPress={() => startEdit(type)} hitSlop={8} accessibilityRole="button">
                  <Text style={styles.rowValue}>{formatCurrency(price)} ✏️</Text>
                </Pressable>
              )}
            </View>
          ))}
        </View>

        <Pressable
          style={styles.continueBtn}
          onPress={() => navigation.navigate('Schedule')}
          accessibilityRole="button"
          accessibilityLabel="Continue to schedule"
        >
          <Text style={styles.continueBtnText}>Looks good →</Text>
        </Pressable>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg.primary },
  scroll: { padding: spacing.xxl, gap: spacing.lg, paddingBottom: 40 },
  title: { ...typography.heading, color: colors.text.primary },
  subtitle: { ...typography.body, color: colors.text.secondary },
  sectionTitle: { ...typography.subheading, color: colors.text.primary, marginTop: spacing.md },
  sectionSubtitle: { ...typography.caption, color: colors.text.tertiary, marginTop: -spacing.sm },
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
  priceInput: {
    ...typography.mono,
    color: colors.text.primary,
    borderBottomWidth: 1,
    borderBottomColor: colors.accent,
    minWidth: 70,
    textAlign: 'right',
    padding: 4,
  },
  continueBtn: {
    backgroundColor: colors.accent,
    paddingVertical: spacing.lg,
    borderRadius: 14,
    alignItems: 'center',
    minHeight: 56,
    justifyContent: 'center',
    marginTop: spacing.md,
  },
  continueBtnText: { ...typography.subheading, color: colors.white, fontSize: 17 },
});
