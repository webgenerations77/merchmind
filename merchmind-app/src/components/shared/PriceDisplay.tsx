import React from 'react';
import { Text, StyleSheet, TextStyle } from 'react-native';
import { colors, typography } from '../../theme';
import { formatCurrency } from '../../utils/formatters';

interface Props {
  amount: number;
  style?: TextStyle;
  size?: 'sm' | 'md' | 'lg';
}

export function PriceDisplay({ amount, style, size = 'md' }: Props) {
  return (
    <Text style={[styles.price, styles[size], style]}>
      {formatCurrency(amount)}
    </Text>
  );
}

const styles = StyleSheet.create({
  price: {
    ...typography.mono,
    color: colors.text.primary,
  },
  sm: { fontSize: 13 },
  md: { fontSize: 15 },
  lg: { fontSize: 20, fontWeight: '700' },
});
