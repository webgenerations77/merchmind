export const SWIPE_THRESHOLD = 80;
export const SWIPE_VELOCITY_THRESHOLD = 800;

export const PRODUCT_TYPE_LABELS: Record<string, string> = {
  t_shirt: 'T-Shirt',
  mug: 'Mug',
  hat: 'Hat',
  sticker: 'Sticker',
  phone_case: 'Phone Case',
};

export const NICHE_CLUSTERS = [
  {
    id: 'pet-obsessed',
    name: 'Pet Obsessed',
    emoji: '🐾',
    keywords: ['dog mom', 'cat dad', 'rescue pet', 'corgi life', 'golden hour'],
  },
  {
    id: 'gym-culture',
    name: 'Gym Culture',
    emoji: '💪',
    keywords: ['lift heavy', 'gains', 'no days off', 'leg day', 'PR mode'],
  },
  {
    id: 'pop-culture',
    name: 'Pop Culture',
    emoji: '🎬',
    keywords: ['stan culture', 'nostalgia', 'meme lord', 'fandom', 'iconic'],
  },
  {
    id: 'seasonal',
    name: 'Seasonal & Holiday',
    emoji: '🎄',
    keywords: ['Christmas', 'Halloween', 'summer vibes', 'fall aesthetic', 'New Year'],
  },
  {
    id: 'profession',
    name: 'Profession Pride',
    emoji: '👩‍⚕️',
    keywords: ['nurse life', 'teacher mode', 'engineer brain', 'chef mindset', 'dev humor'],
  },
];

export const CHANNEL_LABELS: Record<string, string> = {
  instagram: 'Instagram',
  tiktok: 'TikTok',
  pinterest: 'Pinterest',
  email: 'Email',
  blog: 'Blog',
};

export const SEVERITY_ICONS: Record<string, string> = {
  info: 'ℹ️',
  warning: '⚠️',
  critical: '🚨',
};

export const BATCH_STEPS = [
  'Scanning Google Trends',
  'Scanning Reddit',
  'Scanning Twitter/X',
  'Scoring ideas',
  'Generating designs',
  'Building mockups',
  'Calculating prices',
  'Creating marketing assets',
  'Finalizing batch',
];

export const HOLIDAY_LABELS: Record<string, string> = {
  '07-04': '🎆 Independence Day week',
  '10-31': '🎃 Halloween week',
  '11-25': '🦃 Thanksgiving week',
  '12-25': '🎄 Christmas week',
  '01-01': '🎉 New Year week',
  '02-14': '❤️ Valentine\'s Day week',
  '05-12': '💐 Mother\'s Day week',
  '06-16': '👔 Father\'s Day week',
};
