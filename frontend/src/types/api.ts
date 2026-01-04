export interface ResearchRequest {
  brand: string;
  country: string;
  industry: string;
  max_results?: number;
  language?: string;
  use_cache?: boolean;
}

export interface Competitor {
  name: string;
  website: string;
  summary: string;
}

export interface Source {
  title: string;
  url: string;
  summary: string;
}

export interface ResearchResponse {
  brand: string;
  country: string;
  industry: string;
  competitors: Competitor[];
  trends: string[];
  ad_insights: string[];
  sources: Source[];
  summary: string;
}

export interface StrategyRequest {
  brand: string;
  industry: string;
  goals: string[];
  budget_usd: number;
  country: string;
  time_horizon_months: number;
  language?: string;
  use_cache?: boolean;
  research: ResearchResponse;
}

export interface BudgetAllocation {
  [channel: string]: number;
}

export interface ContentPlan {
  [contentType: string]: {
    cadence_per_week: number;
    platforms: string[];
  };
}

export interface SWOTAnalysis {
  strengths: string[];
  weaknesses: string[];
  opportunities: string[];
  threats: string[];
}

export interface TimelinePhase {
  phase: string;
  start: string;
  end: string;
}

export interface MediaCalendarItem {
  week: number;
  channel: string;
  budget_usd: number;
}

export interface StrategyResponse {
  brand: string;
  total_budget_usd: number;
  allocations: BudgetAllocation;
  content_plan: ContentPlan;
  kpis: string[];
  swot: SWOTAnalysis;
  timeline: TimelinePhase[];
  media_calendar: MediaCalendarItem[];
}

export interface WorkflowRequest {
  brand: string;
  country: string;
  industry: string;
  goals: string[];
  budget_usd: number;
  time_horizon_months: number;
  max_results?: number;
}

export interface WorkflowResponse {
  research: ResearchResponse;
  strategy: StrategyResponse;
}

export interface ReportGenerationRequest {
  brand: string;
  language?: string;
  use_cache?: boolean;
  research: ResearchResponse;
  strategy: StrategyResponse;
}

export interface ApiError {
  detail: string;
  status_code: number;
}