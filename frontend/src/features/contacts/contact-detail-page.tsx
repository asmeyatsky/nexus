import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import { contactsApi } from "./contacts-api";
import { useAuth } from "@/features/auth/auth-context";
import { PageHeader } from "@/components/shared/page-header";
import { LoadingSpinner } from "@/components/shared/loading-spinner";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { ContactForm } from "./contact-form";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function ContactDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [showDelete, setShowDelete] = useState(false);

  const { data: contact, isLoading } = useQuery({
    queryKey: ["contacts", id],
    queryFn: () => contactsApi.get(id!),
  });

  const updateMutation = useMutation({
    mutationFn: (data: Parameters<typeof contactsApi.create>[0]) => contactsApi.update(id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contacts", id] });
      toast.success("Contact updated");
    },
    onError: () => toast.error("Failed to update contact"),
  });

  const deleteMutation = useMutation({
    mutationFn: () => contactsApi.delete(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contacts"] });
      navigate("/contacts");
      toast.success("Contact deleted");
    },
  });

  if (isLoading || !contact) return <LoadingSpinner />;

  return (
    <div>
      <PageHeader
        title={`${contact.first_name} ${contact.last_name}`}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => navigate("/contacts")}>
              <ArrowLeft className="mr-2 h-4 w-4" /> Back
            </Button>
            <Button variant="destructive" size="sm" onClick={() => setShowDelete(true)}>
              Delete
            </Button>
          </div>
        }
      />

      <Card>
        <CardHeader><CardTitle>Contact Details</CardTitle></CardHeader>
        <CardContent>
          <ContactForm
            defaultValues={contact}
            ownerId={user!.id}
            onSubmit={(d) => updateMutation.mutate(d)}
            loading={updateMutation.isPending}
          />
        </CardContent>
      </Card>

      <ConfirmDialog
        open={showDelete}
        onOpenChange={setShowDelete}
        title="Delete Contact"
        description="This action cannot be undone."
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={() => deleteMutation.mutate()}
        loading={deleteMutation.isPending}
      />
    </div>
  );
}
