import React from 'react';
import { View, Text, StyleSheet, Dimensions } from 'react-native';
import { VictoryLine, VictoryChart, VictoryAxis, VictoryArea } from 'victory-native';
import { colors, typography, spacing } from '../../theme';
import { formatCurrency } from '../../utils/formatters';

interface DataPoint {
  week: string;
  revenue: number;
}

interface Props {
  data: DataPoint[];
  title?: string;
}

const CHART_WIDTH = Dimensions.get('window').width - spacing.xxl * 2;

export function RevenueChart({ data, title }: Props) {
  const chartData = data.map((d, i) => ({ x: i + 1, y: d.revenue }));

  if (chartData.length === 0) {
    return (
      <View style={styles.container}>
        {title && <Text style={styles.title}>{title}</Text>}
        <Text style={styles.empty}>No data available</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {title && <Text style={styles.title}>{title}</Text>}
      <VictoryChart width={CHART_WIDTH} height={160} padding={{ top: 10, bottom: 30, left: 50, right: 10 }}>
        <VictoryAxis
          tickFormat={() => ''}
          style={{ axis: { stroke: colors.border }, ticks: { stroke: 'transparent' } }}
        />
        <VictoryAxis
          dependentAxis
          tickFormat={(v: number) => `$${v}`}
          style={{
            axis: { stroke: colors.border },
            tickLabels: { fill: colors.text.tertiary, fontSize: 10 },
            grid: { stroke: colors.border, strokeDasharray: '4 4' },
          }}
        />
        <VictoryArea
          data={chartData}
          style={{
            data: {
              fill: `${colors.accent}33`,
              stroke: colors.accent,
              strokeWidth: 2,
            },
          }}
          interpolation="monotoneX"
        />
      </VictoryChart>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.bg.secondary,
    borderRadius: 12,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
  },
  title: {
    ...typography.subheading,
    color: colors.text.primary,
    marginBottom: spacing.sm,
  },
  empty: {
    ...typography.body,
    color: colors.text.tertiary,
    textAlign: 'center',
    paddingVertical: spacing.xxl,
  },
});
