import React, { useEffect } from 'react';
import { View, StyleSheet, ViewStyle } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withTiming,
  interpolate,
} from 'react-native-reanimated';
import { colors } from '../../theme';

interface SkeletonBoxProps {
  width?: number | string;
  height?: number;
  borderRadius?: number;
  style?: ViewStyle;
}

export function SkeletonBox({ width = '100%', height = 16, borderRadius = 4, style }: SkeletonBoxProps) {
  const shimmer = useSharedValue(0);

  useEffect(() => {
    shimmer.value = withRepeat(withTiming(1, { duration: 1200 }), -1, true);
  }, [shimmer]);

  const animatedStyle = useAnimatedStyle(() => ({
    opacity: interpolate(shimmer.value, [0, 1], [0.3, 0.7]),
  }));

  return (
    <Animated.View
      style={[
        styles.skeleton,
        { width: width as number, height, borderRadius },
        animatedStyle,
        style,
      ]}
    />
  );
}

export function ReviewCardSkeleton() {
  return (
    <View style={styles.card}>
      <SkeletonBox height={240} borderRadius={12} />
      <View style={{ marginTop: 8, gap: 6 }}>
        <SkeletonBox height={14} width="70%" />
        <SkeletonBox height={12} width="40%" />
      </View>
    </View>
  );
}

export function ProductRowSkeleton() {
  return (
    <View style={styles.row}>
      <SkeletonBox width={56} height={56} borderRadius={8} />
      <View style={{ flex: 1, gap: 6, marginLeft: 12 }}>
        <SkeletonBox height={14} width="80%" />
        <SkeletonBox height={12} width="50%" />
      </View>
      <SkeletonBox width={60} height={20} borderRadius={6} />
    </View>
  );
}

const styles = StyleSheet.create({
  skeleton: {
    backgroundColor: colors.bg.tertiary,
  },
  card: {
    flex: 1,
    margin: 4,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
});
