import React from 'react';
import { View, Text, StyleSheet, Dimensions } from 'react-native';
import { VictoryScatter, VictoryChart, VictoryAxis } from 'victory-native';
import { colors, typography, spacing } from '../../theme';

interface DataPoint {
  trendScore: number;
  revenue: number;
  conceptName: string;
}

interface Props {
  data: DataPoint[];
}

const CHART_WIDTH = Dimensions.get('window').width - spacing.xxl * 2;

export function TrendCorrelationChart({ data }: Props) {
  const chartData = data.map(d => ({ x: d.trendScore, y: d.revenue }));

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Trend Score vs Revenue</Text>
      <Text style={styles.subtitle}>Does a high score mean high sales?</Text>
      <VictoryChart width={CHART_WIDTH} height={200} padding={{ top: 10, bottom: 40, left: 50, right: 10 }}>
        <VictoryAxis
          label="Trend Score"
          style={{
            axis: { stroke: colors.border },
            tickLabels: { fill: colors.text.tertiary, fontSize: 10 },
            axisLabel: { fill: colors.text.tertiary, fontSize: 10, padding: 28 },
          }}
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
        <VictoryScatter
          data={chartData}
          size={6}
          style={{ data: { fill: colors.accent, opacity: 0.8 } }}
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
  },
  subtitle: {
    ...typography.caption,
    color: colors.text.tertiary,
    marginBottom: spacing.xs,
  },
});
