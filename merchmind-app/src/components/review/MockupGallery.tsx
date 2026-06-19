import React, { useState, useRef } from 'react';
import {
  View,
  ScrollView,
  Text,
  Pressable,
  StyleSheet,
  Dimensions,
  NativeScrollEvent,
  NativeSyntheticEvent,
} from 'react-native';
import FastImage from 'react-native-fast-image';
import { colors, spacing, typography } from '../../theme';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const GALLERY_HEIGHT = SCREEN_WIDTH * 0.75;

interface Props {
  mockupUrls: Record<string, string[]>;
}

export function MockupGallery({ mockupUrls }: Props) {
  const productTypes = Object.keys(mockupUrls);
  const [activeType, setActiveType] = useState(productTypes[0] ?? '');
  const [activeIndex, setActiveIndex] = useState(0);
  const scrollRef = useRef<ScrollView>(null);

  const images = mockupUrls[activeType] ?? [];

  const handleScroll = (e: NativeSyntheticEvent<NativeScrollEvent>) => {
    const index = Math.round(e.nativeEvent.contentOffset.x / SCREEN_WIDTH);
    setActiveIndex(index);
  };

  const switchType = (type: string) => {
    setActiveType(type);
    setActiveIndex(0);
    scrollRef.current?.scrollTo({ x: 0, animated: false });
  };

  return (
    <View style={styles.container}>
      {productTypes.length > 1 && (
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          style={styles.tabBar}
          contentContainerStyle={styles.tabBarContent}
        >
          {productTypes.map(type => (
            <Pressable
              key={type}
              style={[styles.tab, activeType === type && styles.tabActive]}
              onPress={() => switchType(type)}
              accessibilityRole="tab"
              accessibilityState={{ selected: activeType === type }}
              hitSlop={8}
            >
              <Text style={[styles.tabText, activeType === type && styles.tabTextActive]}>
                {type.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}
              </Text>
            </Pressable>
          ))}
        </ScrollView>
      )}

      <ScrollView
        ref={scrollRef}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        onMomentumScrollEnd={handleScroll}
        style={styles.gallery}
      >
        {images.map((url, i) => (
          <View key={i} style={styles.imageWrapper}>
            <FastImage
              source={{ uri: url, priority: FastImage.priority.high }}
              style={styles.image}
              resizeMode={FastImage.resizeMode.cover}
            />
          </View>
        ))}
      </ScrollView>

      {images.length > 1 && (
        <View style={styles.dots}>
          {images.map((_, i) => (
            <View
              key={i}
              style={[styles.dot, i === activeIndex && styles.dotActive]}
            />
          ))}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.bg.secondary,
  },
  tabBar: {
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  tabBarContent: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    gap: spacing.sm,
  },
  tab: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: colors.border,
    minHeight: 32,
    alignItems: 'center',
    justifyContent: 'center',
  },
  tabActive: {
    borderColor: colors.accent,
    backgroundColor: `${colors.accent}22`,
  },
  tabText: {
    ...typography.caption,
    color: colors.text.secondary,
  },
  tabTextActive: {
    color: colors.accent,
    fontWeight: '600',
  },
  gallery: {
    height: GALLERY_HEIGHT,
  },
  imageWrapper: {
    width: SCREEN_WIDTH,
    height: GALLERY_HEIGHT,
    backgroundColor: colors.bg.tertiary,
  },
  image: {
    width: '100%',
    height: '100%',
  },
  dots: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: spacing.sm,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.text.tertiary,
  },
  dotActive: {
    backgroundColor: colors.accent,
    width: 16,
  },
});
