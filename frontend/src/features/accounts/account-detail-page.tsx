import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import { accountsApi } from "./accounts-api";
import { useAuth } from "@/features/auth/auth-context";
import { PageHeader } from "@/components/shared/page-header";
import { LoadingSpinner } from "@/components/shared/loading-spinner";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { AccountForm } from "./account-form";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DataTable, type Column } from "@/components/shared/data-table";
import apiClient from "@/lib/api-client";
import type { Contact } from "@/features/contacts/contacts-types";
import type { Opportunity } from "@/features/opportunities/opportunities-types";

const contactColumns: Column<Contact>[] = [
  { header: "Name", accessor: (r) => `${r.first_name} ${r.last_name}` },
  { header: "Email", accessor: "email" },
  { header: "Title", accessor: (r) => r.title ?? "-" },
];

const oppColumns: Column<Opportunity>[] = [
  { header: "Name", accessor: "name" },
  { header: "Stage", accessor: (r) => r.stage.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) },
  { header: "Amount", accessor: (r) => `$${r.amount.toLocaleString()}` },
];

export function AccountDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [showDeactivate, setShowDeactivate] = useState(false);
  const [showDelete, setShowDelete] = useState(false);

  const { data: account, isLoading } = useQuery({
    queryKey: ["accounts", id],
    queryFn: () => accountsApi.get(id!),
  });

  const contacts = useQuery({
    queryKey: ["accounts", id, "contacts"],
    queryFn: () => apiClient.get<Contact[]>(`/accounts/${id}/contacts`).then((r) => r.data),
  });

  const opportunities = useQuery({
    queryKey: ["accounts", id, "opportunities"],
    queryFn: () =>
      apiClient.get<Opportunity[]>("/opportunities", { params: { limit: 100 } }).then((r) =>
        r.data.filter((o) => o.account_id === id)
      ),
  });

  const updateMutation = useMutation({
    mutationFn: (data: Parameters<typeof accountsApi.create>[0]) => accountsApi.update(id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts", id] });
      toast.success("Account updated");
    },
    onError: () => toast.error("Failed to update account"),
  });

  const deactivateMutation = useMutation({
    mutationFn: () => accountsApi.deactivate(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      setShowDeactivate(false);
      toast.success("Account deactivated");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => accountsApi.delete(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      navigate("/accounts");
      toast.success("Account deleted");
    },
  });

  if (isLoading || !account) return <LoadingSpinner />;

  return (
    <div>
      <PageHeader
        title={account.name}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => navigate("/accounts")}>
              <ArrowLeft className="mr-2 h-4 w-4" /> Back
            </Button>
            {account.is_active && (
              <Button variant="outline" size="sm" onClick={() => setShowDeactivate(true)}>
                Deactivate
              </Button>
            )}
            <Button variant="destructive" size="sm" onClick={() => setShowDelete(true)}>
              Delete
            </Button>
          </div>
        }
      />

      <Tabs defaultValue="details">
        <TabsList>
          <TabsTrigger value="details">Details</TabsTrigger>
          <TabsTrigger value="contacts">Contacts</TabsTrigger>
          <TabsTrigger value="opportunities">Opportunities</TabsTrigger>
        </TabsList>

        <TabsContent value="details">
          <Card>
            <CardHeader>
              <CardTitle>Account Details</CardTitle>
            </CardHeader>
            <CardContent>
              <AccountForm
                defaultValues={account}
                ownerId={user!.id}
                onSubmit={(d) => updateMutation.mutate(d)}
                loading={updateMutation.isPending}
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="contacts">
          <Card>
            <CardHeader><CardTitle>Contacts</CardTitle></CardHeader>
            <CardContent>
              <DataTable
                columns={contactColumns}
                data={contacts.data ?? []}
                isLoading={contacts.isLoading}
                emptyMessage="No contacts for this account"
                onRowClick={(r) => navigate(`/contacts/${r.id}`)}
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="opportunities">
          <Card>
            <CardHeader><CardTitle>Opportunities</CardTitle></CardHeader>
            <CardContent>
              <DataTable
                columns={oppColumns}
                data={opportunities.data ?? []}
                isLoading={opportunities.isLoading}
                emptyMessage="No opportunities for this account"
                onRowClick={(r) => navigate(`/opportunities/${r.id}`)}
              />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <ConfirmDialog
        open={showDeactivate}
        onOpenChange={setShowDeactivate}
        title="Deactivate Account"
        description="Are you sure you want to deactivate this account?"
        confirmLabel="Deactivate"
        onConfirm={() => deactivateMutation.mutate()}
        loading={deactivateMutation.isPending}
      />

      <ConfirmDialog
        open={showDelete}
        onOpenChange={setShowDelete}
        title="Delete Account"
        description="This action cannot be undone. This will permanently delete the account."
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={() => deleteMutation.mutate()}
        loading={deleteMutation.isPending}
      />
    </div>
  );
}
