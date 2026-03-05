import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { leadsApi } from "./leads-api";
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
import { LeadForm } from "./lead-form";
import type { Lead } from "./leads-types";

function formatLabel(s: string) {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

const ratingColors: Record<string, string> = {
  hot: "bg-red-100 text-red-800",
  warm: "bg-yellow-100 text-yellow-800",
  cold: "bg-blue-100 text-blue-800",
};

const columns: Column<Lead>[] = [
  { header: "Name", accessor: (r) => `${r.first_name} ${r.last_name}` },
  { header: "Company", accessor: "company" },
  { header: "Status", accessor: (r) => <Badge variant="outline">{formatLabel(r.status)}</Badge> },
  {
    header: "Rating",
    accessor: (r) => (
      <Badge variant="outline" className={ratingColors[r.rating] ?? ""}>
        {formatLabel(r.rating)}
      </Badge>
    ),
  },
];

const STATUSES = [
  { value: "new", label: "New" },
  { value: "contacted", label: "Contacted" },
  { value: "qualified", label: "Qualified" },
  { value: "converted", label: "Converted" },
  { value: "unqualified", label: "Unqualified" },
  { value: "recycled", label: "Recycled" },
];

const RATINGS = [
  { value: "hot", label: "Hot" },
  { value: "warm", label: "Warm" },
  { value: "cold", label: "Cold" },
];

export function LeadsListPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { filters, setFilter, clearFilters, queryParams, hasActiveFilters, page, setPage, limit } = useFilters();
  const { views, saveView, deleteView } = useSavedViews("leads");
  const [showCreate, setShowCreate] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["leads", queryParams],
    queryFn: () => leadsApi.list(queryParams),
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  const createMutation = useMutation({
    mutationFn: leadsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      setShowCreate(false);
      toast.success("Lead created");
    },
    onError: () => toast.error("Failed to create lead"),
  });

  return (
    <div>
      <PageHeader
        title="Leads"
        actions={
          <div className="flex gap-2">
            <SavedViewsDropdown
              views={views}
              onLoad={(f) => { for (const [k, v] of Object.entries(f)) setFilter(k, v); }}
              onSave={(name) => saveView(name, filters)}
              onDelete={deleteView}
            />
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="mr-2 h-4 w-4" /> New Lead
            </Button>
          </div>
        }
      />

      <FilterBar
        search={filters.search}
        onSearchChange={(v) => setFilter("search", v)}
        filters={[
          { key: "status", label: "Status", options: STATUSES },
          { key: "rating", label: "Rating", options: RATINGS },
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
        emptyMessage="No leads found."
        onRowClick={(row) => navigate(`/leads/${row.id}`)}
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
          <DialogHeader><DialogTitle>Create Lead</DialogTitle></DialogHeader>
          <LeadForm
            ownerId={user!.id}
            onSubmit={(d) => createMutation.mutate(d)}
            loading={createMutation.isPending}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}
