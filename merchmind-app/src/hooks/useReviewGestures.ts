import { useSharedValue, useAnimatedStyle, withSpring, withTiming, runOnJS } from 'react-native-reanimated';
import { Gesture } from 'react-native-gesture-handler';
import { SWIPE_THRESHOLD, SWIPE_VELOCITY_THRESHOLD } from '../utils/constants';

interface UseReviewGesturesOptions {
  onApprove: () => void;
  onReject: () => void;
  onDelay: () => void;
}

export function useReviewGestures({ onApprove, onReject, onDelay }: UseReviewGesturesOptions) {
  const translateX = useSharedValue(0);
  const translateY = useSharedValue(0);
  const overlayOpacity = useSharedValue(0);
  const overlayColor = useSharedValue<'approve' | 'reject' | 'delay'>('approve');

  const gesture = Gesture.Pan()
    .onUpdate(e => {
      translateX.value = e.translationX;
      translateY.value = e.translationY;

      const absDx = Math.abs(e.translationX);
      const absDy = Math.abs(e.translationY);

      if (absDy > absDx && e.translationY < -SWIPE_THRESHOLD / 2) {
        overlayColor.value = 'delay';
        overlayOpacity.value = Math.min(1, absDy / SWIPE_THRESHOLD);
      } else if (e.translationX > 0) {
        overlayColor.value = 'approve';
        overlayOpacity.value = Math.min(1, absDx / SWIPE_THRESHOLD);
      } else {
        overlayColor.value = 'reject';
        overlayOpacity.value = Math.min(1, absDx / SWIPE_THRESHOLD);
      }
    })
    .onEnd(e => {
      const absDx = Math.abs(e.translationX);
      const absDy = Math.abs(e.translationY);
      const fastSwipeX = Math.abs(e.velocityX) > SWIPE_VELOCITY_THRESHOLD;
      const fastSwipeY = Math.abs(e.velocityY) > SWIPE_VELOCITY_THRESHOLD;

      const isUpSwipe =
        e.translationY < -SWIPE_THRESHOLD && absDy > absDx;
      const isRightSwipe =
        e.translationX > SWIPE_THRESHOLD || (fastSwipeX && e.translationX > 0);
      const isLeftSwipe =
        e.translationX < -SWIPE_THRESHOLD || (fastSwipeX && e.translationX < 0);
      const isUpFast = fastSwipeY && e.translationY < 0 && absDy > absDx;

      if (isUpSwipe || isUpFast) {
        runOnJS(onDelay)();
        translateX.value = withSpring(0);
        translateY.value = withSpring(0);
        overlayOpacity.value = withTiming(0);
      } else if (isRightSwipe) {
        runOnJS(onApprove)();
        translateX.value = withSpring(0);
        translateY.value = withSpring(0);
        overlayOpacity.value = withTiming(0);
      } else if (isLeftSwipe) {
        runOnJS(onReject)();
        translateX.value = withSpring(0);
        translateY.value = withSpring(0);
        overlayOpacity.value = withTiming(0);
      } else {
        translateX.value = withSpring(0);
        translateY.value = withSpring(0);
        overlayOpacity.value = withTiming(0);
      }
    });

  const cardStyle = useAnimatedStyle(() => ({
    transform: [
      { translateX: translateX.value },
      { translateY: translateY.value },
      { rotate: `${translateX.value * 0.05}deg` },
    ],
  }));

  return { gesture, cardStyle, overlayOpacity, overlayColor };
}
