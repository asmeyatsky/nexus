export interface Case {
  id: string;
  case_number: string;
  subject: string;
  description: string;
  account_id: string;
  contact_id?: string;
  status: string;
  priority: string;
  origin: string;
  owner_id: string;
  resolution_notes?: string;
  resolved_by?: string;
  resolved_at?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateCaseRequest {
  subject: string;
  description: string;
  account_id: string;
  owner_id: string;
  case_number: string;
  contact_id?: string;
  priority?: string;
  origin?: string;
}

export interface ResolveCaseRequest {
  resolution_notes: string;
  resolved_by: string;
}

export const CASE_STATUSES = [
  "new", "in_progress", "waiting_on_customer",
  "waiting_on_third_party", "resolved", "closed",
] as const;

export const CASE_PRIORITIES = ["low", "medium", "high", "critical"] as const;
export const CASE_ORIGINS = ["web", "email", "phone", "chat", "social"] as const;
