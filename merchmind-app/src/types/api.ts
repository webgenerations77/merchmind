// ─── Batch ───────────────────────────────────────────────────────────────────

export type BatchStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'partial';

export interface Batch {
  id: string;
  status: BatchStatus;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  total_designs: number;
  approved_designs: number;
  rejected_designs: number;
  error_message: string | null;
}

export interface BatchProgress {
  step: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  message?: string;
  progress?: number;
}

// ─── Trend ───────────────────────────────────────────────────────────────────

export interface Trend {
  id: string;
  keyword: string;
  source: 'google_trends' | 'reddit' | 'twitter';
  subreddit?: string;
  trend_score: number;
  niche_cluster: string;
  claude_reasoning: string;
  scraped_at: string;
}

// ─── Design ──────────────────────────────────────────────────────────────────

export type DesignStatus =
  | 'pending'
  | 'generating'
  | 'ready'
  | 'approved'
  | 'rejected'
  | 'delayed'
  | 'published'
  | 'failed';

export type DesignArchetype =
  | 'text_only'
  | 'flat_illustration'
  | 'text_icon'
  | 'photo_real'
  | 'minimalist';

export interface DesignColors {
  primary: string;
  secondary: string;
  accent: string;
  background: string;
}

export interface Design {
  id: string;
  batch_id: string;
  trend_id: string;
  status: DesignStatus;
  concept_name: string;
  archetype: DesignArchetype;
  image_prompt: string;
  raw_image_url: string | null;
  processed_image_url: string | null;
  mockup_urls: Record<string, string[]>;
  font_pair: string;
  style_label: string;
  colors: DesignColors;
  listing_title: string;
  listing_tags: string[];
  seo_description: string;
  final_score: number;
  trend_score: number;
  quality_score: number | null;
  is_soft_flagged: boolean;
  flag_reason: string | null;
  version: number;
  parent_design_id: string | null;
  approved_at: string | null;
  rejected_at: string | null;
  delayed_to_week: string | null;
  created_at: string;
  // joined from trend
  claude_reasoning?: string;
  niche_cluster?: string;
  source?: string;
  keyword?: string;
}

export interface DesignQueueItem {
  id: string;
  concept_name: string;
  archetype: DesignArchetype;
  processed_image_url: string | null;
  mockup_urls: Record<string, string[]>;
  final_score: number;
  trend_score: number;
  quality_score: number | null;
  status: DesignStatus;
  is_soft_flagged: boolean;
  flag_reason: string | null;
  font_pair: string;
  style_label: string;
  colors: DesignColors;
  listing_title: string;
  listing_tags: string[];
  seo_description: string;
  claude_reasoning?: string;
  niche_cluster?: string;
  source?: string;
  keyword?: string;
  created_at: string;
}

// ─── Product ─────────────────────────────────────────────────────────────────

export type ProductType =
  | 't_shirt'
  | 'mug'
  | 'hat'
  | 'sticker'
  | 'phone_case'
  | 'poster';

export type PublishStatus =
  | 'queued'
  | 'published'
  | 'failed'
  | 'unpublished'
  | 'draft';

export interface Product {
  id: string;
  design_id: string;
  product_type: ProductType;
  printify_product_id: string | null;
  shopify_product_id: string | null;
  publish_status: PublishStatus;
  base_cost: number;
  retail_price: number;
  trend_boost: number;
  total_revenue: number;
  units_sold: number;
  net_profit: number;
  trend_score: number | null;
  days_live: number;
  published_at: string | null;
  unpublished_at: string | null;
  created_at: string;
  // denormalized from design
  concept_name?: string;
  processed_image_url?: string | null;
  mockup_urls?: Record<string, string[]>;
  listing_title?: string;
  niche_cluster?: string;
}

// ─── Sale ────────────────────────────────────────────────────────────────────

export interface Sale {
  id: string;
  product_id: string;
  sale_date: string;
  quantity: number;
  gross_revenue: number;
  net_profit: number;
  channel: string;
  shopify_order_id: string | null;
}

export interface SalesAnalytics {
  total_revenue: number;
  total_units: number;
  total_profit: number;
  weekly_revenue: number;
  monthly_revenue: number;
  revenue_by_product_type: Record<ProductType, number>;
  revenue_by_channel: Record<string, number>;
  revenue_by_niche: Record<string, number>;
  weekly_series: { week: string; revenue: number }[];
}

// ─── Alert ───────────────────────────────────────────────────────────────────

export type AlertSeverity = 'info' | 'warning' | 'critical';
export type AlertType =
  | 'underperformer'
  | 'publish_failed'
  | 'batch_failed'
  | 'low_inventory'
  | 'empty_batch';

export interface Alert {
  id: string;
  type: AlertType;
  severity: AlertSeverity;
  message: string;
  product_id: string | null;
  design_id: string | null;
  resolved: boolean;
  resolved_at: string | null;
  created_at: string;
}

// ─── Marketing Asset ─────────────────────────────────────────────────────────

export type MarketingChannel =
  | 'instagram'
  | 'tiktok'
  | 'pinterest'
  | 'email'
  | 'blog';

export type AssetStatus = 'pending' | 'approved' | 'failed';

export interface MarketingAsset {
  id: string;
  design_id: string;
  channel: MarketingChannel;
  status: AssetStatus;
  // Instagram
  caption?: string;
  image_url?: string;
  // TikTok
  hook_text?: string;
  full_script?: string;
  // Pinterest
  pin_title?: string;
  pin_description?: string;
  // Email
  subject_lines?: string[];
  preview_text?: string;
  body_html?: string;
  // Blog
  blog_title?: string;
  blog_intro?: string;
  blog_body?: string;
  created_at: string;
}

// ─── Settings ────────────────────────────────────────────────────────────────

export interface FloorPrices {
  t_shirt: number;
  mug: number;
  hat: number;
  sticker: number;
  phone_case: number;
  poster: number;
}

export interface AppSettings {
  id: string;
  base_markup: number;
  trend_boost_max: number;
  floor_prices: FloorPrices;
  quality_threshold: number;
  score_filter: number;
  max_products_per_batch: number;
  batch_schedule_cron: string;
  review_notification_time: string;
  publish_time: string;
  notify_batch_ready: boolean;
  notify_underperformer: boolean;
  notify_publish_failed: boolean;
  expo_push_token: string | null;
  selected_cluster_ids: string[];
  updated_at: string;
}

// ─── Niche Cluster ───────────────────────────────────────────────────────────

export interface NicheCluster {
  id: string;
  name: string;
  emoji: string;
  keywords: string[];
  is_active: boolean;
}

// ─── Onboarding ──────────────────────────────────────────────────────────────

export interface OnboardingStatus {
  connected: {
    anthropic: boolean;
    openai: boolean;
    replicate: boolean;
    printify: boolean;
    shopify: boolean;
    supabase: boolean;
    klaviyo: boolean;
    expo: boolean;
  };
  all_connected: boolean;
}

export interface ValidateKeyResult {
  service: string;
  valid: boolean;
  error?: string;
}

// ─── API Envelope ─────────────────────────────────────────────────────────────

export interface ApiEnvelope<T> {
  success: boolean;
  data: T;
  error: string | null;
}
