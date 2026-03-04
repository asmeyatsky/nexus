export interface Lead {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  company: string;
  status: string;
  rating: string;
  owner_id: string;
  source?: string;
  phone?: string;
  title?: string;
  website?: string;
  converted_account_id?: string;
  converted_contact_id?: string;
  converted_opportunity_id?: string;
  converted_at?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateLeadRequest {
  first_name: string;
  last_name: string;
  email: string;
  company: string;
  owner_id: string;
  source?: string;
  phone?: string;
  title?: string;
  website?: string;
}

export interface ConvertLeadRequest {
  account_id: string;
  contact_id: string;
  opportunity_id?: string;
}

export const LEAD_STATUSES = [
  "new", "contacted", "qualified", "converted", "unqualified", "recycled",
] as const;

export const LEAD_RATINGS = ["hot", "warm", "cold"] as const;
