import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { casesApi } from "./cases-api";
import { usePagination } from "@/hooks/use-pagination";
import { useAuth } from "@/features/auth/auth-context";
import { PageHeader } from "@/components/shared/page-header";
import { DataTable, type Column } from "@/components/shared/data-table";
import { PaginationControls } from "@/components/shared/pagination-controls";
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

export function CasesListPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { limit, offset, page, nextPage, prevPage } = usePagination();
  const [showCreate, setShowCreate] = useState(false);
  const [showOpen, setShowOpen] = useState(false);

  const { data = [], isLoading } = useQuery({
    queryKey: ["cases", { limit, offset, open: showOpen }],
    queryFn: () =>
      showOpen ? casesApi.listOpen({ limit, offset }) : casesApi.list({ limit, offset }),
  });

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
            <Button variant="outline" onClick={() => setShowOpen(!showOpen)}>
              {showOpen ? "Show All" : "Open Only"}
            </Button>
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="mr-2 h-4 w-4" /> New Case
            </Button>
          </div>
        }
      />

      <DataTable
        columns={columns}
        data={data}
        isLoading={isLoading}
        emptyMessage="No cases found."
        onRowClick={(row) => navigate(`/cases/${row.id}`)}
      />

      <PaginationControls page={page} hasMore={data.length === limit} onPrev={prevPage} onNext={nextPage} />

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
