export interface Contact {
  id: string;
  account_id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone?: string;
  title?: string;
  department?: string;
  owner_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateContactRequest {
  account_id: string;
  first_name: string;
  last_name: string;
  email: string;
  owner_id: string;
  phone?: string;
  title?: string;
  department?: string;
}
