import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { accountsApi } from "./accounts-api";
import { usePagination } from "@/hooks/use-pagination";
import { useAuth } from "@/features/auth/auth-context";
import { PageHeader } from "@/components/shared/page-header";
import { DataTable, type Column } from "@/components/shared/data-table";
import { PaginationControls } from "@/components/shared/pagination-controls";
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

export function AccountsListPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { limit, offset, page, nextPage, prevPage } = usePagination();
  const [showCreate, setShowCreate] = useState(false);

  const { data = [], isLoading } = useQuery({
    queryKey: ["accounts", { limit, offset }],
    queryFn: () => accountsApi.list({ limit, offset }),
  });

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
          <Button onClick={() => setShowCreate(true)}>
            <Plus className="mr-2 h-4 w-4" /> New Account
          </Button>
        }
      />

      <DataTable
        columns={columns}
        data={data}
        isLoading={isLoading}
        emptyMessage="No accounts found. Create your first account."
        onRowClick={(row) => navigate(`/accounts/${row.id}`)}
      />

      <PaginationControls
        page={page}
        hasMore={data.length === limit}
        onPrev={prevPage}
        onNext={nextPage}
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
