import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { opportunitiesApi } from "./opportunities-api";
import { useFilters } from "@/hooks/use-filters";
import { useSavedViews } from "@/hooks/use-saved-views";
import { useAuth } from "@/features/auth/auth-context";
import { PageHeader } from "@/components/shared/page-header";
import { DataTable, type Column } from "@/components/shared/data-table";
import { PaginationControls } from "@/components/shared/pagination-controls";
import { FilterBar } from "@/components/shared/filter-bar";
import { SavedViewsDropdown } from "@/components/shared/saved-views-dropdown";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { OpportunityForm } from "./opportunity-form";
import { StageBadge } from "./stage-badge";
import type { Opportunity } from "./opportunities-types";

const columns: Column<Opportunity>[] = [
  { header: "Name", accessor: "name" },
  { header: "Stage", accessor: (r) => <StageBadge stage={r.stage} /> },
  { header: "Amount", accessor: (r) => `$${r.amount.toLocaleString()}` },
  { header: "Probability", accessor: (r) => `${r.probability}%` },
  { header: "Close Date", accessor: (r) => new Date(r.close_date).toLocaleDateString() },
];

const STAGES = [
  { value: "prospecting", label: "Prospecting" },
  { value: "qualification", label: "Qualification" },
  { value: "needs_analysis", label: "Needs Analysis" },
  { value: "value_proposition", label: "Value Proposition" },
  { value: "decision_makers", label: "Decision Makers" },
  { value: "proposal", label: "Proposal" },
  { value: "negotiation", label: "Negotiation" },
  { value: "closed_won", label: "Closed Won" },
  { value: "closed_lost", label: "Closed Lost" },
];

export function OpportunitiesListPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { filters, setFilter, clearFilters, queryParams, hasActiveFilters, page, setPage, limit } = useFilters();
  const { views, saveView, deleteView } = useSavedViews("opportunities");
  const [showCreate, setShowCreate] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["opportunities", queryParams],
    queryFn: () => opportunitiesApi.list(queryParams),
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  const createMutation = useMutation({
    mutationFn: opportunitiesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["opportunities"] });
      setShowCreate(false);
      toast.success("Opportunity created");
    },
    onError: () => toast.error("Failed to create opportunity"),
  });

  return (
    <div>
      <PageHeader
        title="Opportunities"
        actions={
          <div className="flex gap-2">
            <SavedViewsDropdown
              views={views}
              onLoad={(f) => { for (const [k, v] of Object.entries(f)) setFilter(k, v); }}
              onSave={(name) => saveView(name, filters)}
              onDelete={deleteView}
            />
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="mr-2 h-4 w-4" /> New Opportunity
            </Button>
          </div>
        }
      />

      <FilterBar
        search={filters.search}
        onSearchChange={(v) => setFilter("search", v)}
        filters={[
          { key: "stage", label: "Stage", options: STAGES },
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
        emptyMessage="No opportunities found."
        onRowClick={(row) => navigate(`/opportunities/${row.id}`)}
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
          <DialogHeader><DialogTitle>Create Opportunity</DialogTitle></DialogHeader>
          <OpportunityForm
            ownerId={user!.id}
            onSubmit={(d) => createMutation.mutate(d)}
            loading={createMutation.isPending}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}
