import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { opportunitiesApi } from "./opportunities-api";
import { usePagination } from "@/hooks/use-pagination";
import { useAuth } from "@/features/auth/auth-context";
import { PageHeader } from "@/components/shared/page-header";
import { DataTable, type Column } from "@/components/shared/data-table";
import { PaginationControls } from "@/components/shared/pagination-controls";
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

export function OpportunitiesListPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { limit, offset, page, nextPage, prevPage } = usePagination();
  const [showCreate, setShowCreate] = useState(false);
  const [showOpen, setShowOpen] = useState(false);

  const { data = [], isLoading } = useQuery({
    queryKey: ["opportunities", { limit, offset, open: showOpen }],
    queryFn: () =>
      showOpen
        ? opportunitiesApi.listOpen({ limit, offset })
        : opportunitiesApi.list({ limit, offset }),
  });

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
            <Button variant="outline" onClick={() => setShowOpen(!showOpen)}>
              {showOpen ? "Show All" : "Open Only"}
            </Button>
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="mr-2 h-4 w-4" /> New Opportunity
            </Button>
          </div>
        }
      />

      <DataTable
        columns={columns}
        data={data}
        isLoading={isLoading}
        emptyMessage="No opportunities found."
        onRowClick={(row) => navigate(`/opportunities/${row.id}`)}
      />

      <PaginationControls page={page} hasMore={data.length === limit} onPrev={prevPage} onNext={nextPage} />

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
