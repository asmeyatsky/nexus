import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import { leadsApi } from "./leads-api";
import { useAuth } from "@/features/auth/auth-context";
import { PageHeader } from "@/components/shared/page-header";
import { LoadingSpinner } from "@/components/shared/loading-spinner";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { ConvertLeadDialog } from "./convert-lead-dialog";
import { LeadForm } from "./lead-form";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function formatLabel(s: string) {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function LeadDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [showDelete, setShowDelete] = useState(false);
  const [showConvert, setShowConvert] = useState(false);

  const { data: lead, isLoading } = useQuery({
    queryKey: ["leads", id],
    queryFn: () => leadsApi.get(id!),
  });

  const qualifyMutation = useMutation({
    mutationFn: () => leadsApi.qualify(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      toast.success("Lead qualified");
    },
    onError: () => toast.error("Failed to qualify lead"),
  });

  const convertMutation = useMutation({
    mutationFn: (data: Parameters<typeof leadsApi.convert>[1]) => leadsApi.convert(id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      setShowConvert(false);
      toast.success("Lead converted");
    },
    onError: () => toast.error("Failed to convert lead"),
  });

  const deleteMutation = useMutation({
    mutationFn: () => leadsApi.delete(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      navigate("/leads");
      toast.success("Lead deleted");
    },
  });

  if (isLoading || !lead) return <LoadingSpinner />;

  const isConvertible = lead.status === "qualified";
  const isQualifiable = lead.status === "new" || lead.status === "contacted";

  return (
    <div>
      <PageHeader
        title={`${lead.first_name} ${lead.last_name}`}
        description={lead.company}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => navigate("/leads")}>
              <ArrowLeft className="mr-2 h-4 w-4" /> Back
            </Button>
            {isQualifiable && (
              <Button variant="outline" size="sm" onClick={() => qualifyMutation.mutate()} disabled={qualifyMutation.isPending}>
                Qualify
              </Button>
            )}
            {isConvertible && (
              <Button size="sm" onClick={() => setShowConvert(true)}>
                Convert
              </Button>
            )}
            <Button variant="destructive" size="sm" onClick={() => setShowDelete(true)}>
              Delete
            </Button>
          </div>
        }
      />

      <div className="mb-4 flex gap-2">
        <Badge variant="outline">{formatLabel(lead.status)}</Badge>
        <Badge variant="outline">{formatLabel(lead.rating)}</Badge>
      </div>

      <Card>
        <CardHeader><CardTitle>Lead Details</CardTitle></CardHeader>
        <CardContent>
          <LeadForm
            defaultValues={lead}
            ownerId={user!.id}
            onSubmit={() => toast.info("Lead updates not supported via this form — use qualify/convert actions")}
          />
        </CardContent>
      </Card>

      <ConvertLeadDialog
        open={showConvert}
        onOpenChange={setShowConvert}
        onConvert={(data) => convertMutation.mutate(data)}
        loading={convertMutation.isPending}
      />

      <ConfirmDialog
        open={showDelete}
        onOpenChange={setShowDelete}
        title="Delete Lead"
        description="This action cannot be undone."
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={() => deleteMutation.mutate()}
        loading={deleteMutation.isPending}
      />
    </div>
  );
}
