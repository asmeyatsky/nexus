import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { contactsApi } from "./contacts-api";
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
  const { filters, setFilter, clearFilters, queryParams, hasActiveFilters, page, setPage, limit } = useFilters();
  const { views, saveView, deleteView } = useSavedViews("contacts");
  const [showCreate, setShowCreate] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["contacts", queryParams],
    queryFn: () => contactsApi.list(queryParams),
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;

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
          <div className="flex gap-2">
            <SavedViewsDropdown
              views={views}
              onLoad={(f) => { for (const [k, v] of Object.entries(f)) setFilter(k, v); }}
              onSave={(name) => saveView(name, filters)}
              onDelete={deleteView}
            />
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="mr-2 h-4 w-4" /> New Contact
            </Button>
          </div>
        }
      />

      <FilterBar
        search={filters.search}
        onSearchChange={(v) => setFilter("search", v)}
        filters={[]}
        filterValues={filters}
        onFilterChange={setFilter}
        onClear={clearFilters}
        hasActiveFilters={hasActiveFilters}
      />

      <DataTable
        columns={columns}
        data={items}
        isLoading={isLoading}
        emptyMessage="No contacts found."
        onRowClick={(row) => navigate(`/contacts/${row.id}`)}
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
