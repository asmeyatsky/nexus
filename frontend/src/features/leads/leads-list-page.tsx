import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { leadsApi } from "./leads-api";
import { usePagination } from "@/hooks/use-pagination";
import { useAuth } from "@/features/auth/auth-context";
import { PageHeader } from "@/components/shared/page-header";
import { DataTable, type Column } from "@/components/shared/data-table";
import { PaginationControls } from "@/components/shared/pagination-controls";
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

export function LeadsListPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { limit, offset, page, nextPage, prevPage } = usePagination();
  const [showCreate, setShowCreate] = useState(false);

  const { data = [], isLoading } = useQuery({
    queryKey: ["leads", { limit, offset }],
    queryFn: () => leadsApi.list({ limit, offset }),
  });

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
          <Button onClick={() => setShowCreate(true)}>
            <Plus className="mr-2 h-4 w-4" /> New Lead
          </Button>
        }
      />

      <DataTable
        columns={columns}
        data={data}
        isLoading={isLoading}
        emptyMessage="No leads found."
        onRowClick={(row) => navigate(`/leads/${row.id}`)}
      />

      <PaginationControls page={page} hasMore={data.length === limit} onPrev={prevPage} onNext={nextPage} />

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
