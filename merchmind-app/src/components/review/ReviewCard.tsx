import React, { memo } from 'react';
import { View, Text, Pressable, StyleSheet, Dimensions } from 'react-native';
import FastImage from 'react-native-fast-image';
import Animated, { useAnimatedStyle, useSharedValue, withSpring, withTiming, runOnJS } from 'react-native-reanimated';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import { colors, typography, spacing } from '../../theme';
import { ConfidenceBadge } from '../shared/ConfidenceBadge';
import { getConfidenceLevel } from '../../utils/formatters';
import { haptics } from '../../utils/haptics';
import { SWIPE_THRESHOLD, SWIPE_VELOCITY_THRESHOLD } from '../../utils/constants';
import type { DesignQueueItem } from '../../types/api';

const CARD_WIDTH = (Dimensions.get('window').width - spacing.lg * 2 - spacing.sm) / 2;
const CARD_HEIGHT = CARD_WIDTH * (4 / 3);

interface Props {
  design: DesignQueueItem;
  onPress: () => void;
  onApprove: () => void;
  onReject: () => void;
  onDelay: () => void;
}

const ReviewCard = memo(function ReviewCard({ design, onPress, onApprove, onReject, onDelay }: Props) {
  const translateX = useSharedValue(0);
  const translateY = useSharedValue(0);
  const overlayOpacity = useSharedValue(0);
  const overlayColor = useSharedValue('approve');

  const triggerApprove = () => { haptics.approve(); onApprove(); };
  const triggerReject = () => { haptics.reject(); onReject(); };
  const triggerDelay = () => { haptics.delay(); onDelay(); };

  const panGesture = Gesture.Pan()
    .onUpdate(e => {
      translateX.value = e.translationX;
      translateY.value = e.translationY;
      const absDx = Math.abs(e.translationX);
      const absDy = Math.abs(e.translationY);
      if (absDy > absDx && e.translationY < 0) {
        overlayColor.value = 'delay';
        overlayOpacity.value = Math.min(0.8, absDy / SWIPE_THRESHOLD);
      } else if (e.translationX > 0) {
        overlayColor.value = 'approve';
        overlayOpacity.value = Math.min(0.8, absDx / SWIPE_THRESHOLD);
      } else {
        overlayColor.value = 'reject';
        overlayOpacity.value = Math.min(0.8, absDx / SWIPE_THRESHOLD);
      }
    })
    .onEnd(e => {
      const absDx = Math.abs(e.translationX);
      const absDy = Math.abs(e.translationY);
      const fastX = Math.abs(e.velocityX) > SWIPE_VELOCITY_THRESHOLD;
      const fastY = Math.abs(e.velocityY) > SWIPE_VELOCITY_THRESHOLD;

      const up = (e.translationY < -SWIPE_THRESHOLD && absDy > absDx) || (fastY && e.velocityY < 0 && absDy > absDx);
      const right = e.translationX > SWIPE_THRESHOLD || (fastX && e.translationX > 0);
      const left = e.translationX < -SWIPE_THRESHOLD || (fastX && e.translationX < 0);

      if (up) {
        runOnJS(triggerDelay)();
      } else if (right) {
        runOnJS(triggerApprove)();
      } else if (left) {
        runOnJS(triggerReject)();
      }

      translateX.value = withSpring(0);
      translateY.value = withSpring(0);
      overlayOpacity.value = withTiming(0);
    });

  const tapGesture = Gesture.Tap().onEnd(() => {
    runOnJS(onPress)();
  });

  const composed = Gesture.Simultaneous(panGesture, tapGesture);

  const cardStyle = useAnimatedStyle(() => ({
    transform: [
      { translateX: translateX.value },
      { translateY: translateY.value },
      { rotate: `${translateX.value * 0.08}deg` },
    ],
  }));

  const overlayStyle = useAnimatedStyle(() => ({
    opacity: overlayOpacity.value,
    backgroundColor:
      overlayColor.value === 'approve'
        ? colors.action.approve
        : overlayColor.value === 'delay'
        ? colors.action.delay
        : colors.action.reject,
  }));

  const imageUrl = design.mockup_urls?.t_shirt?.[0] ?? design.processed_image_url ?? '';
  const hasFlag = design.is_soft_flagged;

  return (
    <GestureDetector gesture={composed}>
      <Animated.View style={[styles.card, cardStyle]}>
        <View style={styles.imageContainer}>
          {imageUrl ? (
            <FastImage
              source={{ uri: imageUrl, priority: FastImage.priority.normal }}
              style={styles.image}
              resizeMode={FastImage.resizeMode.cover}
            />
          ) : (
            <View style={[styles.image, styles.imagePlaceholder]} />
          )}
          <Animated.View style={[StyleSheet.absoluteFill, styles.overlay, overlayStyle]} />
          {hasFlag && (
            <View style={styles.flagBadge}>
              <Text style={styles.flagText}>⚠️</Text>
            </View>
          )}
        </View>
        <View style={styles.footer}>
          <Text style={styles.name} numberOfLines={1}>{design.concept_name}</Text>
          <ConfidenceBadge score={design.final_score} size="sm" />
        </View>
      </Animated.View>
    </GestureDetector>
  );
});

export { ReviewCard };

const styles = StyleSheet.create({
  card: {
    width: CARD_WIDTH,
    borderRadius: 12,
    overflow: 'hidden',
    backgroundColor: colors.bg.secondary,
    borderWidth: 1,
    borderColor: colors.border,
    marginBottom: spacing.sm,
  },
  imageContainer: {
    width: CARD_WIDTH,
    height: CARD_HEIGHT,
    backgroundColor: colors.bg.tertiary,
  },
  image: {
    width: '100%',
    height: '100%',
  },
  imagePlaceholder: {
    backgroundColor: colors.bg.tertiary,
  },
  overlay: {
    borderRadius: 12,
  },
  flagBadge: {
    position: 'absolute',
    top: spacing.sm,
    right: spacing.sm,
    backgroundColor: `${'#EAB308'}33`,
    borderRadius: 12,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  flagText: { fontSize: 12 },
  footer: {
    padding: spacing.sm,
    gap: 4,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  name: {
    ...typography.caption,
    color: colors.text.primary,
    fontWeight: '600',
    flex: 1,
  },
});
