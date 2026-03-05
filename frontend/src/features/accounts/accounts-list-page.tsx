import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { accountsApi } from "./accounts-api";
import { useFilters } from "@/hooks/use-filters";
import { useSavedViews } from "@/hooks/use-saved-views";
import { useAuth } from "@/features/auth/auth-context";
import { PageHeader } from "@/components/shared/page-header";
import { DataTable, type Column } from "@/components/shared/data-table";
import { PaginationControls } from "@/components/shared/pagination-controls";
import { FilterBar } from "@/components/shared/filter-bar";
import { SavedViewsDropdown } from "@/components/shared/saved-views-dropdown";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { AccountForm } from "./account-form";
import type { Account } from "./accounts-types";

function formatLabel(s: string) {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

const columns: Column<Account>[] = [
  { header: "Name", accessor: "name" },
  { header: "Industry", accessor: (r) => formatLabel(r.industry) },
  { header: "Territory", accessor: (r) => formatLabel(r.territory) },
  {
    header: "Status",
    accessor: (r) => (
      <Badge variant={r.is_active ? "default" : "secondary"}>
        {r.is_active ? "Active" : "Inactive"}
      </Badge>
    ),
  },
];

const INDUSTRIES = [
  { value: "technology", label: "Technology" },
  { value: "finance", label: "Finance" },
  { value: "healthcare", label: "Healthcare" },
  { value: "manufacturing", label: "Manufacturing" },
  { value: "retail", label: "Retail" },
  { value: "education", label: "Education" },
  { value: "government", label: "Government" },
  { value: "nonprofit", label: "Nonprofit" },
  { value: "other", label: "Other" },
];

const TERRITORIES = [
  { value: "north_america", label: "North America" },
  { value: "europe", label: "Europe" },
  { value: "asia_pacific", label: "Asia Pacific" },
  { value: "latin_america", label: "Latin America" },
  { value: "middle_east", label: "Middle East" },
  { value: "africa", label: "Africa" },
];

export function AccountsListPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { filters, setFilter, clearFilters, queryParams, hasActiveFilters, page, setPage, limit } = useFilters();
  const { views, saveView, deleteView } = useSavedViews("accounts");
  const [showCreate, setShowCreate] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["accounts", queryParams],
    queryFn: () => accountsApi.list(queryParams),
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  const createMutation = useMutation({
    mutationFn: accountsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      setShowCreate(false);
      toast.success("Account created");
    },
    onError: () => toast.error("Failed to create account"),
  });

  return (
    <div>
      <PageHeader
        title="Accounts"
        actions={
          <div className="flex gap-2">
            <SavedViewsDropdown
              views={views}
              onLoad={(f) => { for (const [k, v] of Object.entries(f)) setFilter(k, v); }}
              onSave={(name) => saveView(name, filters)}
              onDelete={deleteView}
            />
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="mr-2 h-4 w-4" /> New Account
            </Button>
          </div>
        }
      />

      <FilterBar
        search={filters.search}
        onSearchChange={(v) => setFilter("search", v)}
        filters={[
          { key: "industry", label: "Industry", options: INDUSTRIES },
          { key: "territory", label: "Territory", options: TERRITORIES },
        ]}
        filterValues={filters}
        onFilterChange={setFilter}
        onClear={clearFilters}
        hasActiveFilters={hasActiveFilters}
      />

      <DataTable
        columns={columns}
        data={items}
        isLoading={isLoading}
        emptyMessage="No accounts found. Create your first account."
        onRowClick={(row) => navigate(`/accounts/${row.id}`)}
      />

      <PaginationControls
        page={page}
        hasMore={page * limit < total}
        onPrev={() => setPage(page - 1)}
        onNext={() => setPage(page + 1)}
        total={total}
        limit={limit}
      />

      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Create Account</DialogTitle>
          </DialogHeader>
          <AccountForm
            ownerId={user!.id}
            onSubmit={(d) => createMutation.mutate(d)}
            loading={createMutation.isPending}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}
