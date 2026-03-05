export interface FilterCondition {
  field: string;
  operator: string;
  value: string;
}

export interface ReportConfig {
  entity: string;
  columns?: string[];
  filters?: FilterCondition[];
  sort_by?: string;
  sort_order: string;
  group_by?: string;
  limit: number;
  chart_type: "table" | "bar" | "pie" | "line";
}

export interface EntityFieldDef {
  name: string;
  label: string;
  type: "string" | "number" | "boolean" | "date";
  enumValues?: { value: string; label: string }[];
}

export const OPERATORS = [
  { value: "eq", label: "Equals" },
  { value: "neq", label: "Not Equals" },
  { value: "contains", label: "Contains" },
  { value: "gt", label: "Greater Than" },
  { value: "lt", label: "Less Than" },
  { value: "gte", label: ">=" },
  { value: "lte", label: "<=" },
  { value: "is_empty", label: "Is Empty" },
  { value: "is_not_empty", label: "Is Not Empty" },
];

export const ENTITY_FIELDS: Record<string, EntityFieldDef[]> = {
  accounts: [
    { name: "name", label: "Name", type: "string" },
    { name: "industry", label: "Industry", type: "string", enumValues: [
      { value: "technology", label: "Technology" }, { value: "finance", label: "Finance" },
      { value: "healthcare", label: "Healthcare" }, { value: "manufacturing", label: "Manufacturing" },
      { value: "retail", label: "Retail" }, { value: "education", label: "Education" },
      { value: "government", label: "Government" }, { value: "nonprofit", label: "Nonprofit" },
      { value: "other", label: "Other" },
    ]},
    { name: "territory", label: "Territory", type: "string", enumValues: [
      { value: "north_america", label: "North America" }, { value: "europe", label: "Europe" },
      { value: "asia_pacific", label: "Asia Pacific" }, { value: "latin_america", label: "Latin America" },
      { value: "middle_east", label: "Middle East" }, { value: "africa", label: "Africa" },
    ]},
    { name: "is_active", label: "Active", type: "boolean" },
    { name: "annual_revenue", label: "Annual Revenue", type: "number" },
    { name: "employee_count", label: "Employee Count", type: "number" },
    { name: "owner_id", label: "Owner ID", type: "string" },
    { name: "created_at", label: "Created At", type: "date" },
  ],
  contacts: [
    { name: "first_name", label: "First Name", type: "string" },
    { name: "last_name", label: "Last Name", type: "string" },
    { name: "email", label: "Email", type: "string" },
    { name: "title", label: "Title", type: "string" },
    { name: "department", label: "Department", type: "string" },
    { name: "is_active", label: "Active", type: "boolean" },
    { name: "account_id", label: "Account ID", type: "string" },
    { name: "created_at", label: "Created At", type: "date" },
  ],
  opportunities: [
    { name: "name", label: "Name", type: "string" },
    { name: "stage", label: "Stage", type: "string", enumValues: [
      { value: "prospecting", label: "Prospecting" }, { value: "qualification", label: "Qualification" },
      { value: "needs_analysis", label: "Needs Analysis" }, { value: "value_proposition", label: "Value Proposition" },
      { value: "decision_makers", label: "Decision Makers" }, { value: "proposal", label: "Proposal" },
      { value: "negotiation", label: "Negotiation" }, { value: "closed_won", label: "Closed Won" },
      { value: "closed_lost", label: "Closed Lost" },
    ]},
    { name: "amount", label: "Amount", type: "number" },
    { name: "probability", label: "Probability", type: "number" },
    { name: "is_closed", label: "Closed", type: "boolean" },
    { name: "is_won", label: "Won", type: "boolean" },
    { name: "close_date", label: "Close Date", type: "date" },
    { name: "source", label: "Source", type: "string" },
    { name: "created_at", label: "Created At", type: "date" },
  ],
  leads: [
    { name: "first_name", label: "First Name", type: "string" },
    { name: "last_name", label: "Last Name", type: "string" },
    { name: "email", label: "Email", type: "string" },
    { name: "company", label: "Company", type: "string" },
    { name: "status", label: "Status", type: "string", enumValues: [
      { value: "new", label: "New" }, { value: "contacted", label: "Contacted" },
      { value: "qualified", label: "Qualified" }, { value: "converted", label: "Converted" },
      { value: "unqualified", label: "Unqualified" }, { value: "recycled", label: "Recycled" },
    ]},
    { name: "rating", label: "Rating", type: "string", enumValues: [
      { value: "hot", label: "Hot" }, { value: "warm", label: "Warm" }, { value: "cold", label: "Cold" },
    ]},
    { name: "source", label: "Source", type: "string" },
    { name: "created_at", label: "Created At", type: "date" },
  ],
  cases: [
    { name: "case_number", label: "Case Number", type: "string" },
    { name: "subject", label: "Subject", type: "string" },
    { name: "status", label: "Status", type: "string", enumValues: [
      { value: "new", label: "New" }, { value: "in_progress", label: "In Progress" },
      { value: "waiting_on_customer", label: "Waiting on Customer" },
      { value: "waiting_on_third_party", label: "Waiting on 3rd Party" },
      { value: "resolved", label: "Resolved" }, { value: "closed", label: "Closed" },
    ]},
    { name: "priority", label: "Priority", type: "string", enumValues: [
      { value: "low", label: "Low" }, { value: "medium", label: "Medium" }, { value: "high", label: "High" },
    ]},
    { name: "origin", label: "Origin", type: "string", enumValues: [
      { value: "web", label: "Web" }, { value: "email", label: "Email" },
      { value: "phone", label: "Phone" }, { value: "chat", label: "Chat" }, { value: "social", label: "Social" },
    ]},
    { name: "account_id", label: "Account ID", type: "string" },
    { name: "created_at", label: "Created At", type: "date" },
  ],
};
