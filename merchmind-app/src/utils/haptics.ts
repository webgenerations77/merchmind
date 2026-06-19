import ReactNativeHapticFeedback from 'react-native-haptic-feedback';

const options = { enableVibrateFallback: true, ignoreAndroidSystemSettings: false };

export const haptics = {
  approve: () => ReactNativeHapticFeedback.trigger('impactHeavy', options),
  reject: () => ReactNativeHapticFeedback.trigger('impactLight', options),
  regen: () => ReactNativeHapticFeedback.trigger('notificationWarning', options),
  delay: () => ReactNativeHapticFeedback.trigger('impactMedium', options),
  error: () => ReactNativeHapticFeedback.trigger('notificationError', options),
  success: () => ReactNativeHapticFeedback.trigger('notificationSuccess', options),
  selection: () => ReactNativeHapticFeedback.trigger('selection', options),
};
