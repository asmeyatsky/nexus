export interface Opportunity {
  id: string;
  account_id: string;
  name: string;
  stage: string;
  amount: number;
  currency: string;
  probability: number;
  close_date: string;
  owner_id: string;
  contact_id?: string;
  source?: string;
  description?: string;
  is_active: boolean;
  is_won: boolean;
  is_lost: boolean;
  is_closed: boolean;
  weighted_value: number;
  created_at: string;
  updated_at: string;
}

export interface CreateOpportunityRequest {
  account_id: string;
  name: string;
  amount: number;
  currency: string;
  close_date: string;
  owner_id: string;
  source?: string;
  contact_id?: string;
  description?: string;
}

export interface UpdateStageRequest {
  stage: string;
  reason?: string;
}

export const OPPORTUNITY_STAGES = [
  "prospecting",
  "qualification",
  "needs_analysis",
  "value_proposition",
  "decision_makers",
  "proposal",
  "negotiation",
  "closed_won",
  "closed_lost",
] as const;

export const OPPORTUNITY_SOURCES = [
  "inbound", "outbound", "referral", "partner", "trade_show", "web", "other",
] as const;
