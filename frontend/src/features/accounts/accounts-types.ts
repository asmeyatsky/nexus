export interface Account {
  id: string;
  name: string;
  industry: string;
  territory: string;
  website?: string;
  phone?: string;
  billing_address?: string;
  annual_revenue?: number;
  currency?: string;
  employee_count?: number;
  owner_id: string;
  parent_account_id?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateAccountRequest {
  name: string;
  industry: string;
  territory: string;
  owner_id: string;
  website?: string;
  phone?: string;
  billing_address?: string;
  annual_revenue?: number;
  currency?: string;
  employee_count?: number;
}

export const INDUSTRIES = [
  "technology", "finance", "healthcare", "manufacturing",
  "retail", "education", "government", "nonprofit", "other",
] as const;

export const TERRITORIES = [
  "north_america", "europe", "asia_pacific",
  "latin_america", "middle_east", "africa",
] as const;
