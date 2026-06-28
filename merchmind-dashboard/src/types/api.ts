export interface ApiResponse<T> {
  success: boolean;
  data: T;
  error: string | null;
}

export interface DesignQueueItem {
  id: string;
  batch_id: string | null;
  concept_name: string;
  archetype: string;
  processed_image_url: string | null;
  quality_score: number;
  shopify_title: string | null;
  classification: string | null;
  status: string;
  collection_id: string | null;
  collection_name?: string;
  source?: 'batch' | 'collection' | 'drews_mind';
  primary_product_type?: string;
  primary_mockup_url?: string;
  image_api_used?: string | null;
  ai_cost?: number;
  is_featured: boolean;
  featured_at?: string | null;
  product_count: number;
  revisit_count?: number;
  claude_reasoning: string | null;
}

export interface DesignOut {
  id: string;
  trend_id: string | null;
  batch_id: string | null;
  collection_id: string | null;
  concept_name: string;
  archetype: string;
  image_api_used: string | null;
  image_prompt: string | null;
  raw_image_url: string | null;
  processed_image_url: string | null;
  font_pair: string | null;
  font_reasoning: string | null;
  color_palette: string[] | null;
  primary_text: string | null;
  secondary_text: string | null;
  tagline: string | null;
  text_concept_scoring: {
    candidates: {
      text: string;
      scores: Record<string, number>;
      total: number;
      rationale: string;
    }[];
    selected_index: number;
  } | null;
  design_style: string | null;
  quality_score: number;
  quality_breakdown: Record<string, number> | null;
  version: number;
  parent_design_id: string | null;
  shopify_title: string | null;
  shopify_description: string | null;
  shopify_tags: string[] | null;
  classification: string | null;
  primary_product_type: string | null;
  primary_product_type_reasoning: string | null;
  is_featured: boolean;
  featured_at: string | null;
  conversation_history: { role: 'user' | 'assistant'; content: string }[] | null;
  status: string;
  delayed_to_week: string | null;
  approved_at: string | null;
  rejected_at: string | null;
  archived_at: string | null;
  revisit_count: number;
  created_at: string;
  // Trend reasoning (populated from joined trend record)
  trend_source?: string | null;
  trend_signal?: string | null;
  trend_source_metadata?: Record<string, unknown> | null;
  trend_score?: number | null;
  viability_score?: number | null;
  final_score?: number | null;
  claude_reasoning?: string | null;
}

export interface BatchOut {
  id: string;
  week_start: string;
  run_started_at: string;
  run_completed_at: string | null;
  status: string;
  total_ideas: number;
  queued_count: number;
  approved_count: number;
  rejected_count: number;
  delayed_count: number;
  error_log: { time: string; error: string }[];
  created_at: string;
}

export interface BatchItemOut {
  id: string;
  batch_id: string;
  trend_id: string | null;
  design_id: string | null;
  concept_name: string;
  status: string;
  failed_step: string | null;
  error_summary: string | null;
  error_detail: string | null;
  product_types: string[];
  started_at: string;
  completed_at: string | null;
  created_at: string;
  processed_image_url: string | null;
}

export interface BatchDetailOut {
  batch: BatchOut;
  items: BatchItemOut[];
  success_count: number;
  failed_count: number;
}

export interface ProductOut {
  id: string;
  design_id: string;
  product_type: string;
  printify_product_id: string | null;
  shopify_product_id: string | null;
  printify_base_cost: number;
  base_markup: number;
  trend_adjustment: number;
  retail_price: number;
  floor_price: number;
  margin_flag: boolean;
  variants: unknown[];
  mockup_urls: Record<string, string>;
  publish_status: string;
  published_at: string | null;
  unpublished_at: string | null;
  drop_id: string | null;
  target_store: 'store_1' | 'store_2' | null;
  created_at: string;
  concept_name: string | null;
  batch_id: string | null;
  processed_image_url: string | null;
  primary_mockup_url: string | null;
}

export interface AlertOut {
  id: string;
  type: string;
  severity: string;
  product_id: string | null;
  design_id: string | null;
  batch_id: string | null;
  message: string;
  action_url: string | null;
  resolved: boolean;
  resolved_at: string | null;
  created_at: string;
}

export interface AppSettings {
  id: string;
  base_markup: Record<string, number>;
  floor_prices: Record<string, number>;
  trend_boost_max: number;
  publish_time: string | null;
  batch_day: string;
  batch_time: string | null;
  min_queue_size: number;
  max_queue_size: number;
  quality_threshold: number;
  score_threshold: number;
  underperform_weeks: number;
  back_logo_enabled: boolean;
  back_logo_url: string | null;
  back_logo_products: string[] | null;
  shopify_store_url: string | null;
  active_clusters: string[] | null;
  marketing_generation_enabled: boolean;
  social_links: {
    instagram_url: string;
    tiktok_url: string;
    pinterest_url: string;
    facebook_url: string;
  } | null;
  updated_at: string;
}

export interface NicheCluster {
  id: string;
  name: string;
  emoji: string;
  subreddits: string[];
  keywords: string[];
  score_boost: number;
  active: boolean;
  created_at: string;
}

export interface IntegrationHealth {
  ok: boolean;
  any_service_reachable: boolean;
  services: Record<string, { service: string; ok: boolean; error?: string }>;
}

export interface CollectionOut {
  id: string;
  name: string;
  description: string | null;
  style_guide: {
    palette?: string[];
    mood?: string;
    constraints?: string;
    archetype_override?: string;
  };
  max_designs: number;
  status: string;
  design_count: number;
  designs?: {
    id: string;
    concept_name: string;
    archetype: string;
    processed_image_url: string | null;
    quality_score: number;
    status: string;
  }[];
  created_at: string;
  updated_at: string;
}

export interface SalesAnalytics {
  total_revenue: number;
  total_profit: number;
  total_orders: number;
  best_seller_product_id: string | null;
  revenue_by_product_type: Record<string, number>;
  weekly_trend: { week: string; revenue: number }[];
}

export interface MerchDropOut {
  id: string;
  name: string;
  scheduled_at: string;
  status: string;
  product_count: number;
  created_at: string;
  updated_at: string;
}

export interface MerchDropDetail extends MerchDropOut {
  products: {
    id: string;
    design_id: string;
    product_type: string;
    publish_status: string;
    retail_price: number;
    mockup_urls: Record<string, string>;
    concept_name: string;
    processed_image_url: string | null;
  }[];
}
