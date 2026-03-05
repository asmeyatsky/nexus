import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { casesApi } from "./cases-api";
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
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { CaseForm } from "./case-form";
import type { Case } from "./cases-types";

function formatLabel(s: string) {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

const priorityColors: Record<string, string> = {
  low: "bg-gray-100 text-gray-800",
  medium: "bg-blue-100 text-blue-800",
  high: "bg-orange-100 text-orange-800",
  critical: "bg-red-100 text-red-800",
};

const columns: Column<Case>[] = [
  { header: "Case #", accessor: "case_number" },
  { header: "Subject", accessor: "subject" },
  { header: "Status", accessor: (r) => <Badge variant="outline">{formatLabel(r.status)}</Badge> },
  {
    header: "Priority",
    accessor: (r) => (
      <Badge variant="outline" className={priorityColors[r.priority] ?? ""}>
        {formatLabel(r.priority)}
      </Badge>
    ),
  },
  { header: "Origin", accessor: (r) => formatLabel(r.origin) },
];

const STATUSES = [
  { value: "new", label: "New" },
  { value: "in_progress", label: "In Progress" },
  { value: "waiting_on_customer", label: "Waiting on Customer" },
  { value: "waiting_on_third_party", label: "Waiting on Third Party" },
  { value: "resolved", label: "Resolved" },
  { value: "closed", label: "Closed" },
];

const PRIORITIES = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
];

const ORIGINS = [
  { value: "web", label: "Web" },
  { value: "email", label: "Email" },
  { value: "phone", label: "Phone" },
  { value: "chat", label: "Chat" },
  { value: "social", label: "Social" },
];

export function CasesListPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { filters, setFilter, clearFilters, queryParams, hasActiveFilters, page, setPage, limit } = useFilters();
  const { views, saveView, deleteView } = useSavedViews("cases");
  const [showCreate, setShowCreate] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["cases", queryParams],
    queryFn: () => casesApi.list(queryParams),
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  const createMutation = useMutation({
    mutationFn: casesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cases"] });
      setShowCreate(false);
      toast.success("Case created");
    },
    onError: () => toast.error("Failed to create case"),
  });

  return (
    <div>
      <PageHeader
        title="Cases"
        actions={
          <div className="flex gap-2">
            <SavedViewsDropdown
              views={views}
              onLoad={(f) => { for (const [k, v] of Object.entries(f)) setFilter(k, v); }}
              onSave={(name) => saveView(name, filters)}
              onDelete={deleteView}
            />
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="mr-2 h-4 w-4" /> New Case
            </Button>
          </div>
        }
      />

      <FilterBar
        search={filters.search}
        onSearchChange={(v) => setFilter("search", v)}
        filters={[
          { key: "status", label: "Status", options: STATUSES },
          { key: "priority", label: "Priority", options: PRIORITIES },
          { key: "origin", label: "Origin", options: ORIGINS },
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
        emptyMessage="No cases found."
        onRowClick={(row) => navigate(`/cases/${row.id}`)}
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
          <DialogHeader><DialogTitle>Create Case</DialogTitle></DialogHeader>
          <CaseForm
            ownerId={user!.id}
            onSubmit={(d) => createMutation.mutate(d)}
            loading={createMutation.isPending}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}
