import React, { useState } from 'react';
import { View, Text, Pressable, TextInput, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '../../theme';
import { formatCurrency } from '../../utils/formatters';

interface ProductPricing {
  productType: string;
  baseCost: number;
  markup: number;
  trendBoost: number;
  retail: number;
  floorPrice: number;
}

interface Props {
  pricingData: ProductPricing[];
  onPriceOverride: (productType: string, price: number) => void;
}

export function PricingBreakdown({ pricingData, onPriceOverride }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [editingType, setEditingType] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');

  return (
    <View style={styles.container}>
      <Pressable
        onPress={() => setExpanded(v => !v)}
        style={styles.header}
        accessibilityRole="button"
        accessibilityState={{ expanded }}
      >
        <Text style={styles.headerText}>💰 Pricing {expanded ? '▲' : '▾'}</Text>
      </Pressable>

      {expanded && (
        <View style={styles.body}>
          {pricingData.map(item => {
            const aboveFloor = item.retail >= item.floorPrice;
            const isEditing = editingType === item.productType;

            return (
              <View key={item.productType} style={styles.productBlock}>
                <Text style={styles.productType}>
                  {item.productType.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}
                </Text>
                <Row label="Base cost" value={formatCurrency(item.baseCost)} />
                <Row label={`Markup (${item.markup}×)`} value={formatCurrency(item.baseCost * item.markup)} />
                <Row label="Trend boost" value={`+${formatCurrency(item.trendBoost)}`} />
                <View style={styles.divider} />
                <View style={styles.retailRow}>
                  <Text style={styles.retailLabel}>Retail</Text>
                  {isEditing ? (
                    <TextInput
                      value={editValue}
                      onChangeText={setEditValue}
                      keyboardType="decimal-pad"
                      style={styles.priceInput}
                      autoFocus
                      onBlur={() => {
                        const parsed = parseFloat(editValue);
                        if (!isNaN(parsed)) onPriceOverride(item.productType, parsed);
                        setEditingType(null);
                      }}
                      accessibilityLabel="Override price"
                    />
                  ) : (
                    <Pressable
                      onPress={() => {
                        setEditingType(item.productType);
                        setEditValue(item.retail.toFixed(2));
                      }}
                      hitSlop={8}
                      accessibilityRole="button"
                      accessibilityLabel="Edit price"
                    >
                      <Text style={[styles.retailValue, { color: aboveFloor ? colors.confidence.high : '#EAB308' }]}>
                        {formatCurrency(item.retail)} {aboveFloor ? '✅' : '⚠️'}
                      </Text>
                    </Pressable>
                  )}
                </View>
              </View>
            );
          })}
        </View>
      )}
    </View>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  header: {
    padding: spacing.lg,
    minHeight: 44,
    justifyContent: 'center',
  },
  headerText: {
    ...typography.subheading,
    color: colors.text.primary,
  },
  body: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.lg,
    gap: spacing.xl,
  },
  productBlock: {
    gap: 6,
  },
  productType: {
    ...typography.subheading,
    color: colors.text.primary,
    marginBottom: spacing.xs,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  rowLabel: {
    ...typography.body,
    color: colors.text.secondary,
  },
  rowValue: {
    ...typography.mono,
    color: colors.text.primary,
  },
  divider: {
    height: 1,
    backgroundColor: colors.border,
    marginVertical: spacing.xs,
  },
  retailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  retailLabel: {
    ...typography.subheading,
    color: colors.text.primary,
  },
  retailValue: {
    ...typography.mono,
    fontSize: 16,
    fontWeight: '700',
  },
  priceInput: {
    ...typography.mono,
    fontSize: 16,
    color: colors.text.primary,
    borderBottomWidth: 1,
    borderBottomColor: colors.accent,
    minWidth: 80,
    textAlign: 'right',
    padding: 4,
  },
});
