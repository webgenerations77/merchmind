import React from 'react';
import { View, Text, StyleSheet, Dimensions } from 'react-native';
import { VictoryBar, VictoryChart, VictoryAxis, VictoryGroup, VictoryLegend } from 'victory-native';
import { colors, typography, spacing } from '../../theme';

interface WeekData {
  week: string;
  generated: number;
  approved: number;
  published: number;
}

interface Props {
  data: WeekData[];
}

const CHART_WIDTH = Dimensions.get('window').width - spacing.xxl * 2;

export function PipelinePerformanceChart({ data }: Props) {
  const generatedData = data.map((d, i) => ({ x: i + 1, y: d.generated }));
  const approvedData = data.map((d, i) => ({ x: i + 1, y: d.approved }));
  const publishedData = data.map((d, i) => ({ x: i + 1, y: d.published }));

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Pipeline Performance</Text>
      <VictoryChart width={CHART_WIDTH} height={200} padding={{ top: 10, bottom: 30, left: 40, right: 10 }}>
        <VictoryAxis
          tickFormat={() => ''}
          style={{ axis: { stroke: colors.border } }}
        />
        <VictoryAxis
          dependentAxis
          style={{
            axis: { stroke: colors.border },
            tickLabels: { fill: colors.text.tertiary, fontSize: 10 },
            grid: { stroke: colors.border, strokeDasharray: '4 4' },
          }}
        />
        <VictoryGroup offset={8}>
          <VictoryBar data={generatedData} style={{ data: { fill: colors.text.tertiary, width: 6 } }} />
          <VictoryBar data={approvedData} style={{ data: { fill: colors.accent, width: 6 } }} />
          <VictoryBar data={publishedData} style={{ data: { fill: colors.confidence.high, width: 6 } }} />
        </VictoryGroup>
      </VictoryChart>
      <View style={styles.legend}>
        <LegendItem color={colors.text.tertiary} label="Generated" />
        <LegendItem color={colors.accent} label="Approved" />
        <LegendItem color={colors.confidence.high} label="Published" />
      </View>
    </View>
  );
}

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <View style={styles.legendItem}>
      <View style={[styles.legendDot, { backgroundColor: color }]} />
      <Text style={styles.legendText}>{label}</Text>
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
  legend: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: spacing.lg,
    marginTop: spacing.sm,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  legendDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  legendText: {
    ...typography.caption,
    color: colors.text.secondary,
  },
});
