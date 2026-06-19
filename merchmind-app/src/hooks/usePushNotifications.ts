import { useEffect, useRef } from 'react';
import { Platform } from 'react-native';
import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import { updateSettings } from '../api/settings';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

export function usePushNotifications(onNotification?: (notification: Notifications.Notification) => void) {
  const listenerRef = useRef<Notifications.EventSubscription | null>(null);
  const responseListenerRef = useRef<Notifications.EventSubscription | null>(null);

  useEffect(() => {
    registerForPushNotificationsAsync().then(token => {
      if (token) {
        updateSettings({ expo_push_token: token }).catch(() => {});
      }
    });

    listenerRef.current = Notifications.addNotificationReceivedListener(notification => {
      onNotification?.(notification);
    });

    responseListenerRef.current = Notifications.addNotificationResponseReceivedListener(() => {
      // Deep linking handled by navigation via notification data
    });

    return () => {
      listenerRef.current?.remove();
      responseListenerRef.current?.remove();
    };
  }, [onNotification]);
}

async function registerForPushNotificationsAsync(): Promise<string | null> {
  if (!Device.isDevice) return null;

  const { status: existingStatus } = await Notifications.getPermissionsAsync();
  let finalStatus = existingStatus;

  if (existingStatus !== 'granted') {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }

  if (finalStatus !== 'granted') return null;

  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('default', {
      name: 'default',
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: '#6366F1',
    });
  }

  const token = (await Notifications.getExpoPushTokenAsync()).data;
  return token;
}
