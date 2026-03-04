import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { contactsApi } from "./contacts-api";
import { usePagination } from "@/hooks/use-pagination";
import { useAuth } from "@/features/auth/auth-context";
import { PageHeader } from "@/components/shared/page-header";
import { DataTable, type Column } from "@/components/shared/data-table";
import { PaginationControls } from "@/components/shared/pagination-controls";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ContactForm } from "./contact-form";
import type { Contact } from "./contacts-types";

const columns: Column<Contact>[] = [
  { header: "Name", accessor: (r) => `${r.first_name} ${r.last_name}` },
  { header: "Email", accessor: "email" },
  { header: "Title", accessor: (r) => r.title ?? "-" },
  { header: "Department", accessor: (r) => r.department ?? "-" },
];

export function ContactsListPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { limit, offset, page, nextPage, prevPage } = usePagination();
  const [showCreate, setShowCreate] = useState(false);

  const { data = [], isLoading } = useQuery({
    queryKey: ["contacts", { limit, offset }],
    queryFn: () => contactsApi.list({ limit, offset }),
  });

  const createMutation = useMutation({
    mutationFn: contactsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contacts"] });
      setShowCreate(false);
      toast.success("Contact created");
    },
    onError: () => toast.error("Failed to create contact"),
  });

  return (
    <div>
      <PageHeader
        title="Contacts"
        actions={
          <Button onClick={() => setShowCreate(true)}>
            <Plus className="mr-2 h-4 w-4" /> New Contact
          </Button>
        }
      />

      <DataTable
        columns={columns}
        data={data}
        isLoading={isLoading}
        emptyMessage="No contacts found."
        onRowClick={(row) => navigate(`/contacts/${row.id}`)}
      />

      <PaginationControls page={page} hasMore={data.length === limit} onPrev={prevPage} onNext={nextPage} />

      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="max-w-2xl">
          <DialogHeader><DialogTitle>Create Contact</DialogTitle></DialogHeader>
          <ContactForm
            ownerId={user!.id}
            onSubmit={(d) => createMutation.mutate(d)}
            loading={createMutation.isPending}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}
