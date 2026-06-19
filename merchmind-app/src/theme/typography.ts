import { TextStyle } from 'react-native';

export const typography: Record<string, TextStyle> = {
  display: { fontSize: 32, fontWeight: '700', lineHeight: 38 },
  heading: { fontSize: 20, fontWeight: '600', lineHeight: 26 },
  subheading: { fontSize: 16, fontWeight: '600', lineHeight: 22 },
  body: { fontSize: 15, fontWeight: '400', lineHeight: 22 },
  caption: { fontSize: 13, fontWeight: '400', lineHeight: 18 },
  mono: { fontSize: 15, fontFamily: 'Menlo', lineHeight: 20 },
};
